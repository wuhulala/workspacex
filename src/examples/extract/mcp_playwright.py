import asyncio
from typing import Dict, Any, Optional

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    print("请安装: pip install langchain-mcp-adapters")
    MultiServerMCPClient = None


class McpTools:
    """简单的 MCP 工具调用客户端"""

    def __init__(self, mcp_config: Dict[str, Any]) -> None:
        """
        初始化 MCP 工具客户端

        Args:
            mcp_config: MCP 服务器配置字典
        """
        if MultiServerMCPClient is None:
            raise ImportError("请安装 langchain-mcp-adapters 包")

        self.mcp_config = mcp_config
        self.client: Optional[MultiServerMCPClient] = None
        self.tools = []

    async def initialize(self) -> None:
        """初始化 MCP 连接并获取工具"""
        print("🔌 初始化 MCP 连接...")
        self.client = MultiServerMCPClient(self.mcp_config)
        self.tools = await self.client.get_tools()
        print(f"✅ 获取到 {len(self.tools)} 个工具")

    async def call_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        调用指定工具

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            工具执行结果
        """
        if not self.tools:
            raise RuntimeError("请先调用 initialize() 初始化")

        # 查找工具
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            available = [t.name for t in self.tools]
            raise ValueError(f"工具 '{tool_name}' 不存在，可用工具: {available}")

        print(f"🔧 调用工具: {tool_name}")
        result = await tool.ainvoke(params or {})
        print(f"✅ 工具执行完成")
        return result

    async def get_clickable_elements(self, content: str) -> list:
        """
        获取页面中所有可点击的元素，使用改进的解析逻辑
        
        Args:
            content: 页面快照内容
            
        Returns:
            可点击元素列表，包含元素信息和定位方式
        """
        if not self.tools:
            raise RuntimeError("请先调用 initialize() 初始化")
        
        print("🔍 获取页面可点击元素...")
        
        # 解析 YAML 格式的快照内容
        lines = content.split('\n')
        clickable_elements = []
        
        # 定义可点击元素的关键词模式
        clickable_patterns = {
            'link': ['link', 'a[', 'href='],
            'button': ['button', 'btn', 'submit', 'click'],
            'textbox': ['textbox', 'input', 'textarea', 'search'],
            'select': ['select', 'dropdown', 'option'],
            'checkbox': ['checkbox', 'check'],
            'radio': ['radio', 'option'],
            'clickable': ['clickable', 'onclick', 'cursor:pointer']
        }
        
        for line in lines:
            line = line.strip()
            if not line or not 'ref=' in line:
                continue
            
            # 提取 ref 标识符
            ref_match = self._extract_ref(line)
            if not ref_match:
                continue
            
            # 检查元素是否可点击
            element_type, element_info = self._analyze_element_type(line, clickable_patterns)
            
            if element_type and element_info:
                # 添加额外的可点击性检查
                if await self._is_element_clickable(ref_match, element_type):
                    clickable_elements.append({
                        "type": element_type,
                        "ref": ref_match,
                        **element_info,
                        "action": self._get_action_for_type(element_type),
                        "description": self._generate_description(element_type, element_info)
                    })
        
        # 去重和排序
        clickable_elements = self._deduplicate_elements(clickable_elements)
        
        print(f"✅ 找到 {len(clickable_elements)} 个可交互元素")
        return clickable_elements
    
    def _extract_ref(self, line: str) -> Optional[str]:
        """
        从行中提取 ref 标识符
        
        Args:
            line: 包含元素信息的行
            
        Returns:
            ref 标识符或 None
        """
        if 'ref=' not in line:
            return None
            
        ref_start = line.find('ref=') + 4
        ref_end = line.find(' ', ref_start)
        if ref_end == -1:
            ref_end = line.find(']', ref_start)
        if ref_end == -1:
            ref_end = line.find('"', ref_start)
        
        if ref_end != -1:
            return line[ref_start:ref_end].strip('"')
        return None
    
    def _analyze_element_type(self, line: str, patterns: Dict[str, list]) -> tuple:
        """
        分析元素类型和提取相关信息
        
        Args:
            line: 元素行
            patterns: 元素类型模式字典
            
        Returns:
            (元素类型, 元素信息字典) 或 (None, None)
        """
        line_lower = line.lower()
        
        # 检查各种元素类型
        for element_type, keywords in patterns.items():
            if any(keyword in line_lower for keyword in keywords):
                element_info = self._extract_element_info(line, element_type)
                if element_info:
                    return element_type, element_info
        
        return None, None
    
    def _extract_element_info(self, line: str, element_type: str) -> Optional[Dict[str, Any]]:
        """
        根据元素类型提取相关信息
        
        Args:
            line: 元素行
            element_type: 元素类型
            
        Returns:
            元素信息字典或 None
        """
        info = {}
        
        # 提取文本内容
        text_match = self._extract_text_content(line)
        if text_match:
            info['text'] = text_match
        
        # 根据元素类型提取特定信息
        if element_type == 'link':
            url_match = self._extract_url(line)
            if url_match:
                info['url'] = url_match
        
        elif element_type == 'textbox':
            placeholder_match = self._extract_placeholder(line)
            if placeholder_match:
                info['placeholder'] = placeholder_match
            # 检查输入框类型
            input_type = self._extract_input_type(line)
            if input_type:
                info['input_type'] = input_type
        
        elif element_type in ['checkbox', 'radio']:
            checked = self._extract_checked_state(line)
            info['checked'] = checked
        
        elif element_type == 'select':
            options = self._extract_select_options(line)
            if options:
                info['options'] = options
        
        return info if info else None
    
    def _extract_text_content(self, line: str) -> Optional[str]:
        """提取元素的文本内容"""
        if '"' in line:
            text_start = line.find('"') + 1
            text_end = line.rfind('"')
            if text_end > text_start:
                return line[text_start:text_end]
        return None
    
    def _extract_url(self, line: str) -> Optional[str]:
        """提取链接的 URL"""
        if '/url:' in line:
            url_start = line.find('/url:') + 5
            return line[url_start:].strip()
        return None
    
    def _extract_placeholder(self, line: str) -> Optional[str]:
        """提取输入框的占位符"""
        if 'placeholder=' in line:
            placeholder_start = line.find('placeholder=') + 12
            placeholder_end = line.find(' ', placeholder_start)
            if placeholder_end == -1:
                placeholder_end = line.find(']', placeholder_start)
            if placeholder_end != -1:
                return line[placeholder_start:placeholder_end].strip('"')
        return None
    
    def _extract_input_type(self, line: str) -> Optional[str]:
        """提取输入框类型"""
        if 'type=' in line:
            type_start = line.find('type=') + 5
            type_end = line.find(' ', type_start)
            if type_end == -1:
                type_end = line.find(']', type_start)
            if type_end != -1:
                return line[type_start:type_end].strip('"')
        return 'text'  # 默认类型
    
    def _extract_checked_state(self, line: str) -> bool:
        """提取复选框或单选框的选中状态"""
        return 'checked' in line.lower()
    
    def _extract_select_options(self, line: str) -> Optional[list]:
        """提取选择框的选项"""
        # 这里需要更复杂的解析逻辑，暂时返回空列表
        return []
    
    async def _is_element_clickable(self, ref: str, element_type: str) -> bool:
        """
        检查元素是否真正可点击
        
        Args:
            ref: 元素引用
            element_type: 元素类型
            
        Returns:
            是否可点击
        """
        try:
            # 使用 Playwright 的可见性检查
            result = await self.call_tool("browser_evaluate", {
                "expression": f"""
                (() => {{
                    const element = document.querySelector('[data-playwright-ref="{ref}"]');
                    if (!element) return false;
                    
                    // 检查元素是否可见
                    const rect = element.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return false;
                    
                    // 检查元素是否在视口内
                    if (rect.top < 0 || rect.left < 0 || 
                        rect.bottom > window.innerHeight || 
                        rect.right > window.innerWidth) return false;
                    
                    // 检查元素是否被其他元素遮挡
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    const topElement = document.elementFromPoint(centerX, centerY);
                    
                    return topElement === element || element.contains(topElement);
                }})()
                """
            })
            
            return result.get('result', False)
        except Exception as e:
            print(f"⚠️ 检查元素可点击性时出错: {e}")
            # 如果检查失败，默认认为可点击
            return True
    
    def _get_action_for_type(self, element_type: str) -> str:
        """根据元素类型获取对应的操作"""
        action_map = {
            'link': 'click_link',
            'button': 'click_button',
            'textbox': 'fill_textbox',
            'select': 'select_option',
            'checkbox': 'toggle_checkbox',
            'radio': 'select_radio',
            'clickable': 'click_element'
        }
        return action_map.get(element_type, 'click_element')
    
    def _generate_description(self, element_type: str, element_info: Dict[str, Any]) -> str:
        """生成元素描述"""
        if element_type == 'link':
            text = element_info.get('text', '链接')
            return f"🔗 链接: {text}"
        elif element_type == 'button':
            text = element_info.get('text', '按钮')
            return f"🔘 按钮: {text}"
        elif element_type == 'textbox':
            placeholder = element_info.get('placeholder', '输入框')
            input_type = element_info.get('input_type', 'text')
            return f"📝 {input_type}输入框: {placeholder}"
        elif element_type == 'select':
            return f"📋 下拉选择框"
        elif element_type == 'checkbox':
            checked = element_info.get('checked', False)
            status = "已选中" if checked else "未选中"
            return f"☑️ 复选框 ({status})"
        elif element_type == 'radio':
            checked = element_info.get('checked', False)
            status = "已选中" if checked else "未选中"
            return f"🔘 单选框 ({status})"
        else:
            return f"🖱️ 可点击元素"
    
    def _deduplicate_elements(self, elements: list) -> list:
        """去重元素列表"""
        seen_refs = set()
        unique_elements = []
        
        for element in elements:
            ref = element.get('ref')
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                unique_elements.append(element)
        
        return unique_elements
    
    async def click_element_by_ref(self, ref: str, force: bool = False, timeout: int = 5000) -> Any:
        """
        根据 ref 点击元素，支持多种点击策略
        
        Args:
            ref: 元素的 ref 标识
            force: 是否强制点击（忽略可见性检查）
            timeout: 超时时间（毫秒）
            
        Returns:
            点击操作结果
        """
        if not self.tools:
            raise RuntimeError("请先调用 initialize() 初始化")
        
        print(f"🖱️ 点击元素 ref: {ref}")
        
        # 尝试多种点击策略
        click_strategies = [
            self._click_with_visibility_check,
            self._click_with_javascript,
            self._click_with_force if force else None,
            self._click_with_scroll_into_view
        ]
        
        # 过滤掉 None 策略
        click_strategies = [strategy for strategy in click_strategies if strategy is not None]
        
        last_error = None
        for i, strategy in enumerate(click_strategies):
            try:
                print(f"🔄 尝试点击策略 {i+1}/{len(click_strategies)}")
                result = await strategy(ref, timeout)
                print(f"✅ 点击成功 (策略 {i+1})")
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ 策略 {i+1} 失败: {e}")
                continue
        
        # 所有策略都失败
        raise RuntimeError(f"所有点击策略都失败了，最后错误: {last_error}")
    
    async def _click_with_visibility_check(self, ref: str, timeout: int) -> Any:
        """使用可见性检查的点击"""
        return await self.call_tool("browser_click", {
            "element": ref,
            "timeout": timeout
        })
    
    async def _click_with_javascript(self, ref: str, timeout: int) -> Any:
        """使用 JavaScript 点击"""
        result = await self.call_tool("browser_evaluate", {
            "expression": f"""
            (() => {{
                const element = document.querySelector('[data-playwright-ref="{ref}"]');
                if (!element) {{
                    throw new Error('Element not found');
                }}
                
                // 滚动到元素可见
                element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                
                // 等待一小段时间让滚动完成
                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        element.click();
                        resolve(true);
                    }}, 100);
                }});
            }})()
            """
        })
        
        if not result.get('result', False):
            raise RuntimeError("JavaScript 点击失败")
        
        return result
    
    async def _click_with_force(self, ref: str, timeout: int) -> Any:
        """强制点击（忽略可见性检查）"""
        return await self.call_tool("browser_click", {
            "element": ref,
            "force": True,
            "timeout": timeout
        })
    
    async def _click_with_scroll_into_view(self, ref: str, timeout: int) -> Any:
        """先滚动到元素位置再点击"""
        # 先滚动到元素
        await self.call_tool("browser_evaluate", {
            "expression": f"""
            (() => {{
                const element = document.querySelector('[data-playwright-ref="{ref}"]');
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }})()
            """
        })
        
        # 等待滚动完成
        await asyncio.sleep(0.5)
        
        # 然后点击
        return await self.call_tool("browser_click", {
            "element": ref,
            "timeout": timeout
        })
    
    async def wait_for_element(self, ref: str, timeout: int = 10000) -> bool:
        """
        等待元素出现并可见
        
        Args:
            ref: 元素引用
            timeout: 超时时间（毫秒）
            
        Returns:
            元素是否成功出现
        """
        try:
            result = await self.call_tool("browser_evaluate", {
                "expression": f"""
                (() => {{
                    const element = document.querySelector('[data-playwright-ref="{ref}"]');
                    if (!element) return false;
                    
                    const rect = element.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }})()
                """
            })
            
            return result.get('result', False)
        except Exception as e:
            print(f"⚠️ 等待元素时出错: {e}")
            return False
    
    async def fill_textbox_by_ref(self, ref: str, text: str, clear_first: bool = True, timeout: int = 5000) -> Any:
        """
        根据 ref 填写文本框，支持多种填写策略
        
        Args:
            ref: 文本框的 ref 标识
            text: 要填写的文本
            clear_first: 是否先清空文本框
            timeout: 超时时间（毫秒）
            
        Returns:
            填写操作结果
        """
        if not self.tools:
            raise RuntimeError("请先调用 initialize() 初始化")
        
        print(f"✏️ 填写文本框 ref: {ref}, 内容: {text}")
        
        # 等待元素出现
        if not await self.wait_for_element(ref, timeout):
            raise RuntimeError(f"文本框 {ref} 未找到或不可见")
        
        # 尝试多种填写策略
        fill_strategies = [
            self._fill_with_form_api,
            self._fill_with_javascript,
            self._fill_with_typing
        ]
        
        last_error = None
        for i, strategy in enumerate(fill_strategies):
            try:
                print(f"🔄 尝试填写策略 {i+1}/{len(fill_strategies)}")
                result = await strategy(ref, text, clear_first, timeout)
                print(f"✅ 填写成功 (策略 {i+1})")
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ 策略 {i+1} 失败: {e}")
                continue
        
        # 所有策略都失败
        raise RuntimeError(f"所有填写策略都失败了，最后错误: {last_error}")
    
    async def _fill_with_form_api(self, ref: str, text: str, clear_first: bool, timeout: int) -> Any:
        """使用表单 API 填写"""
        return await self.call_tool("browser_fill_form", {
            "fields": [{"element": ref, "text": text}]
        })
    
    async def _fill_with_javascript(self, ref: str, text: str, clear_first: bool, timeout: int) -> Any:
        """使用 JavaScript 填写"""
        result = await self.call_tool("browser_evaluate", {
            "expression": f"""
            (() => {{
                const element = document.querySelector('[data-playwright-ref="{ref}"]');
                if (!element) {{
                    throw new Error('Element not found');
                }}
                
                // 聚焦元素
                element.focus();
                
                // 清空内容
                if ({str(clear_first).lower()}) {{
                    element.value = '';
                }}
                
                // 设置值
                element.value = '{text}';
                
                // 触发输入事件
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                return true;
            }})()
            """
        })
        
        if not result.get('result', False):
            raise RuntimeError("JavaScript 填写失败")
        
        return result
    
    async def _fill_with_typing(self, ref: str, text: str, clear_first: bool, timeout: int) -> Any:
        """使用模拟打字填写"""
        if clear_first:
            # 先清空
            await self.call_tool("browser_type", {
                "element": ref,
                "text": "",
                "clear": True
            })
        
        # 然后输入文本
        return await self.call_tool("browser_type", {
            "element": ref,
            "text": text
        })
    
    async def fill_multiple_fields(self, fields: list, parallel: bool = True) -> Any:
        """
        填写多个表单字段，支持并行处理
        
        Args:
            fields: 字段列表，每个字段包含 element 和 text
            parallel: 是否并行填写字段
            
        Returns:
            填写操作结果
        """
        if not self.tools:
            raise RuntimeError("请先调用 initialize() 初始化")
        
        print(f"✏️ 填写多个字段: {len(fields)} 个 (并行: {parallel})")
        
        if parallel:
            # 并行填写所有字段
            tasks = []
            for field in fields:
                task = self.fill_textbox_by_ref(
                    field['element'], 
                    field['text'], 
                    clear_first=field.get('clear_first', True)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查是否有失败的
            failed_count = sum(1 for result in results if isinstance(result, Exception))
            if failed_count > 0:
                print(f"⚠️ {failed_count} 个字段填写失败")
            
            print(f"✅ 批量填写完成 (成功: {len(fields) - failed_count}, 失败: {failed_count})")
            return results
        else:
            # 串行填写
            result = await self.call_tool("browser_fill_form", {"fields": fields})
            print(f"✅ 批量填写完成")
            return result
    
    async def find_element_by_text(self, text: str, element_type: str = "any") -> Optional[Dict[str, Any]]:
        """
        根据文本内容查找元素
        
        Args:
            text: 要查找的文本
            element_type: 元素类型限制 ("link", "button", "textbox", "any")
            
        Returns:
            找到的元素信息或 None
        """
        try:
            result = await self.call_tool("browser_evaluate", {
                "expression": f"""
                (() => {{
                    const text = '{text}';
                    const selectors = [
                        'a[href*="' + text + '"]',
                        'button:contains("' + text + '")',
                        'input[placeholder*="' + text + '"]',
                        '[data-testid*="' + text + '"]',
                        '[aria-label*="' + text + '"]',
                        '[title*="' + text + '"]'
                    ];
                    
                    for (const selector of selectors) {{
                        try {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                return {{
                                    found: true,
                                    tagName: element.tagName,
                                    text: element.textContent || element.value || element.placeholder,
                                    href: element.href || null,
                                    type: element.type || null
                                }};
                            }}
                        }} catch (e) {{
                            // 忽略无效选择器
                        }}
                    }}
                    
                    // 如果选择器方法失败，尝试文本匹配
                    const allElements = document.querySelectorAll('*');
                    for (const element of allElements) {{
                        const elementText = element.textContent || element.value || element.placeholder || '';
                        if (elementText.includes(text)) {{
                            return {{
                                found: true,
                                tagName: element.tagName,
                                text: elementText,
                                href: element.href || null,
                                type: element.type || null
                            }};
                        }}
                    }}
                    
                    return {{ found: false }};
                }})()
                """
            })
            
            if result.get('result', {}).get('found', False):
                element_info = result['result']
                return {
                    'tag_name': element_info.get('tagName'),
                    'text': element_info.get('text'),
                    'url': element_info.get('href'),
                    'input_type': element_info.get('type')
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ 查找元素时出错: {e}")
            return None
    
    async def validate_element_interaction(self, ref: str, action: str) -> Dict[str, Any]:
        """
        验证元素是否可以执行指定操作
        
        Args:
            ref: 元素引用
            action: 操作类型 ("click", "fill", "select")
            
        Returns:
            验证结果字典
        """
        try:
            result = await self.call_tool("browser_evaluate", {
                "expression": f"""
                (() => {{
                    const element = document.querySelector('[data-playwright-ref="{ref}"]');
                    if (!element) {{
                        return {{ valid: false, reason: 'Element not found' }};
                    }}
                    
                    const rect = element.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    const isInViewport = rect.top >= 0 && rect.left >= 0 && 
                                       rect.bottom <= window.innerHeight && 
                                       rect.right <= window.innerWidth;
                    
                    let canInteract = false;
                    let reason = '';
                    
                    switch ('{action}') {{
                        case 'click':
                            canInteract = isVisible && !element.disabled && 
                                        !element.hasAttribute('disabled') &&
                                        getComputedStyle(element).pointerEvents !== 'none';
                            reason = canInteract ? 'Clickable' : 'Not clickable';
                            break;
                            
                        case 'fill':
                            canInteract = isVisible && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') &&
                                        !element.readOnly && !element.disabled;
                            reason = canInteract ? 'Fillable' : 'Not fillable';
                            break;
                            
                        case 'select':
                            canInteract = isVisible && element.tagName === 'SELECT' && !element.disabled;
                            reason = canInteract ? 'Selectable' : 'Not selectable';
                            break;
                            
                        default:
                            canInteract = isVisible;
                            reason = canInteract ? 'Interactable' : 'Not interactable';
                    }}
                    
                    return {{
                        valid: canInteract,
                        reason: reason,
                        isVisible: isVisible,
                        isInViewport: isInViewport,
                        tagName: element.tagName,
                        disabled: element.disabled,
                        readOnly: element.readOnly
                    }};
                }})()
                """
            })
            
            return result.get('result', {'valid': False, 'reason': 'Unknown error'})
            
        except Exception as e:
            return {'valid': False, 'reason': f'Validation error: {e}'}

    async def close(self) -> None:
        """关闭连接"""
        if self.client:
            # 注意: 某些版本的客户端可能没有 close 方法
            try:
                await self.client.close()
            except AttributeError:
                pass
            print("🔌 连接已关闭")


DEFAULT_MCP_CONFIG = {
    "playwright-mcp": {
        "command": "npx",
        "args": [
            "@playwright/mcp@latest"
        ],
        "transport": "stdio"
    }
}
# 使用示例


async def main():
    """使用示例 - 演示可点击元素检索功能"""
    # 创建客户端
    tools = McpTools(DEFAULT_MCP_CONFIG)

    try:
        # 初始化
        await tools.initialize()

        url = "https://www.baidu.com"

        # 导航到页面
        print(f"🌐 导航到: {url}")
        result = await tools.call_tool("browser_navigate", {"url": url})
        print(f"导航结果: {result}")

        # 获取页面可点击元素
        clickable_elements = await tools.get_clickable_elements(result)
        
        print(f"\n📋 页面可交互元素列表:")
        for i, element in enumerate(clickable_elements, 1):
            print(f"{i}. {element['description']} (ref: {element['ref']})")
            if element.get('url'):
                print(f"   URL: {element['url']}")
        
        # 示例：智能搜索功能
        print(f"\n🔍 开始智能搜索演示...")
        
        # 方法1：通过可点击元素列表查找
        search_box = None
        for element in clickable_elements:
            if element['type'] == 'textbox' and ('搜索' in element.get('placeholder', '') or 'search' in element.get('placeholder', '').lower()):
                search_box = element
                break
        
        # 方法2：如果没找到，通过文本查找
        if not search_box:
            print("🔄 通过文本查找搜索框...")
            search_element = await tools.find_element_by_text("搜索", "textbox")
            if search_element:
                print(f"✅ 通过文本找到搜索框: {search_element}")
        
        if search_box:
            print(f"✅ 找到搜索框，开始搜索...")
            
            # 验证元素是否可以填写
            validation = await tools.validate_element_interaction(search_box['ref'], 'fill')
            print(f"📋 元素验证结果: {validation}")
            
            if validation['valid']:
                # 填写搜索内容
                await tools.fill_textbox_by_ref(search_box['ref'], "Python编程")
                
                # 查找并点击搜索按钮
                search_button = None
                for element in clickable_elements:
                    if element['type'] == 'button' and ('搜索' in element.get('text', '') or 'search' in element.get('text', '').lower()):
                        search_button = element
                        break
                
                if search_button:
                    # 验证按钮是否可以点击
                    button_validation = await tools.validate_element_interaction(search_button['ref'], 'click')
                    print(f"📋 按钮验证结果: {button_validation}")
                    
                    if button_validation['valid']:
                        await tools.click_element_by_ref(search_button['ref'])
                        print("🔍 搜索完成!")
                    else:
                        print(f"⚠️ 按钮不可点击: {button_validation['reason']}")
                else:
                    print("⚠️ 未找到搜索按钮")
            else:
                print(f"⚠️ 搜索框不可填写: {validation['reason']}")
        else:
            print("⚠️ 未找到搜索框")
        
        # 演示批量填写功能（如果有多个输入框）
        textboxes = [elem for elem in clickable_elements if elem['type'] == 'textbox']
        if len(textboxes) > 1:
            print(f"\n📝 演示批量填写功能...")
            fields_to_fill = []
            for i, textbox in enumerate(textboxes[:2]):  # 只填写前两个
                # 验证每个字段是否可以填写
                validation = await tools.validate_element_interaction(textbox['ref'], 'fill')
                if validation['valid']:
                    fields_to_fill.append({
                        "element": textbox['ref'],
                        "text": f"测试内容 {i+1}",
                        "clear_first": True
                    })
                else:
                    print(f"⚠️ 跳过不可填写的字段: {textbox['ref']} - {validation['reason']}")
            
            if fields_to_fill:
                # 演示并行填写
                print(f"🚀 并行填写 {len(fields_to_fill)} 个字段...")
                await tools.fill_multiple_fields(fields_to_fill, parallel=True)
                print("✅ 批量填写演示完成")
            else:
                print("⚠️ 没有可填写的字段")
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        # 关闭连接
        await tools.close()
        print("🛑 已完成所有操作，连接关闭")

if __name__ == "__main__":
    asyncio.run(main())
