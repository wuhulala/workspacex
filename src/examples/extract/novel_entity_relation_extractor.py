import asyncio
import os
import textwrap

from dotenv import load_dotenv
from langextract.factory import ModelConfig

NOVEL_DEMO = """
第1173章 擒仙
　　金色柳条发出金属碰撞的声音，这些柳叶，这些柳枝居然如同锁链一般，有金属质感，缠绕在王曦的身上，牢牢困缚。
　　“开！”王曦轻叱，满头秀发飞舞，修长的躯体在剧烈挣动，手中的黑暗仙金剑挥动，斩出一串又一串火星。
　　她想破开束缚，斩断这些金色神链，然而却这些柳枝却越发的勒紧了，坚韧不朽。
　　哪怕黑暗仙金剑锋锐，斩断了一些，但是其他部分马上补充过来，这些金色的枝条有一种强横的生命力。
　　“王曦被擒住了！”人们大吃一惊，随后瞠目结舌，一个个都说不出话来。
　　这太让人觉得震撼了，那可是长生家族王家的小姐，一个修出三道仙气的仙子，惊才绝艳，战力无匹，今日却遭擒。
　　“轰！”
　　一片南明离火腾起，王曦化成火炬，从她每一寸雪白的肌肤中喷薄光焰，焚烧那一根又一根枝条。
　　很快，她就被火光淹没了。
　　此时，石昊早已化成一道光冲了过去，快速出手，就要将她拿下。
　　哧！
　　王曦是非常人，尽管肉身暂被束缚，但是依旧能动，撕开虚空，横渡了出去，想要逃离此地。
　　此时她的右臂也被缠住了，手中的黑暗仙金剑离去，在她的元神催动下，斩身上的秩序神链，同时抵挡后方的强敌。
　　可是，这依旧不能阻挡石昊脚步，毕竟她被禁锢了，战力锐减。
　　“轰！”
　　下一刻，王曦的周围冲出十条身影，都是她的灵身，一起向石昊杀去，有朱雀、金乌、九头蛇等各种世上最强的神禽凶兽。
　　当然也有人形的生灵，但都是养在洞天中的灵身，合力围杀石昊。
　　“王曦竟被逼迫到了这一步，开始动用灵身了，真的是没有办法了。”
　　“想不到一代天骄女居然被那曾经追随她的人压制，即将成为俘虏，这让人无言！”
　　所有人都明白，出动灵身是难以改变现状的，因为对手也有灵身，这只能说明王曦走投无路了。
　　人们一叹，这样的天之骄女恐怕是第一次被擒吧？
　　石昊笑了，身体一摇，并不像常人那样一下子出现十口洞天，而只是一团朦胧的光，但是却冲出很多道身影。
　　“鲲鹏？！”一些人惊叫。
　　“人形雷电？”
　　“还有一株柳树？！”
　　……
　　惊呼声此起彼伏，许多人睁大了眼睛。
　　虽然早有预料，在看到那少年施展鲲鹏法，而后又莫名出动柳神宝术时，就已经大致猜测到了他的身份，但这时才算确认。
　　因为，随着石昊出动灵身，跟他所擅长的宝术结合了起来，全都暴露了，道出了他究竟是谁！
　　轰！
　　天崩地裂，鬼哭神嚎，石昊的灵身一起出动，迎击对方的十大灵身，激烈搏击，进行阻杀。
　　很明显，不加掩饰的石昊是强势的，无与伦比，此时每一道灵身都掌握有一种惊世大神通，现在叠加，威力绝伦。
　　这个地方沸腾！
　　“他是荒，竟然没有死，来到了我天神书院！”
　　“元青不是出手了吗，将他送进太初古矿，传闻他已经死在了矿中，为何在这里现身了？”
　　“天啊，原来他就是荒，是下界那个名为石昊的少年，终于得到证实了，我就说嘛，无缘无故怎么可能会出现这样一位年轻至尊！”
　　一片议论声，这些人既激动又兴奋，热切的观战。
　　王曦要被拿下了，人们惊叹，这对王家来说绝对是一件糟糕透顶的事情，要知道这可是该族最惊艳的弟子，修出了三道仙气！
　　况且，这个少年还曾经冒犯他们，让他们感觉羞辱，下不来台，而此前更是跟王曦传出过绯色消息。
　　被这样的一个年轻男子擒住，对于王曦来说，对于王家来说，绝对不是什么好事！
　　砰！
　　虚空中，战斗激烈，有些身影被击飞了，王曦的两道灵身遭遇重创，预料中的结局要落幕了。
　　忽然，一阵难言的压抑瞬间笼罩上众人的心头，包括石昊也如此，暗叫一声不好，快速倒退而去。
　　一道绝世剑芒，从王曦的眉心中冲出，太快了，摇曳着刺目的光华，直接斩向石昊！
　　“那是什么？”
　　“是王曦的元神出窍了吗？”
　　“天啊，这剑气怎么会如此可怕，甚至比平乱诀都要恐怖几分，她是怎么练成的？”
　　许多人惊叫，此时的王曦肉身不动，可是眉心间，有一道神虹出窍，太快了，要击杀掉石昊。
　　只有少数人看的明白，那是王曦的元神出窍，是一个与她一模一样才小女婴，拳头高，抱着一口手指长的黑色小剑，发出万丈光，冲向石昊。
　　那种景象非常诡异！
　　因为，那小人虽然是元神，但是整体流动的不是元神力，而是剑气，形成剑罡，在体表外形成循环。
　　元神力怎么成为了剑气，化作无敌剑罡？
　　众人大惊失色，一个个心惊肉跳。
　　“这不是平乱诀，不过比之更强啊，这是什么剑意？”
　　“错了，这是平乱诀，而且是练到高深地步的体现，将元神都化成了剑胎！”
　　“天啊，这丫头是怎么练成的，也太可怕了，你们看到她手中黑色小剑了吗，如同黑暗仙金般，无坚不摧，那是元神所化啊。如果女婴消失，元神彻底化成一柄剑胎，那么就将无敌了，臻至无上境界！”
　　没有人不动容，元神化成剑胎，古来少有，尤其是这个年龄段，根本就不可能成功，称得上前不见古人。
　　石昊寒毛嗖嗖倒竖，感觉到了一个杀意，那元神冲过来时，凌厉无匹，斩神杀魔，无坚不摧，太可怕了！
　　若非他躲避迅速，直接就被洞穿了！
　　他还真没见过这么可怕的剑罡，从虚空中斩来，破灭万物，最重要的是她太快了，难以躲避。
　　若非他不加掩饰，动用鲲鹏法，一顿神翅扇动，极速闪开，那么刚才就可能被难元神剑胎斩掉头颅了。
　　这也太惊人了！
　　石昊意动躯体，留下一道又一道残影。
　　一道黑色残影划过，快到天眼通都几乎难以捕捉到，这就是平乱诀中的元神剑胎，杀人于无形中，防不胜防。
　　当！
　　火星四溅，响声震耳。
　　与此同时，石昊停下了，不再躲避。
　　“完了，平乱诀中的元神剑胎速度超过思感，这样停下来的话，将再无法躲避，一下子陷入被动中会被击杀的！”有人叹道。
　　“平乱诀简直无解啊！”一些人附和。
　　“当！”
　　又是一声碰撞，石昊怒了，捏拳印，跟那元神剑胎碰撞，火星四溅。
　　“什么，他拥有何等的拳意，竟能跟上王曦的速度，可撼动平乱诀中的元神剑胎？”许多人大惊。
　　须知，元神剑胎超越思感，一旦祭出，原则上可斩一切同阶敌手。
　　“他融合了鲲鹏法等诸多奥义，是凭一种最直接的战斗本能在出手，凭直觉拦住了平乱诀中的元神剑胎！”
　　人们心惊肉跳，那种速度太快了。
　　到了现在，他们已经根本看不到王曦的元神剑胎，即便睁开天眼，也只能看到一道残影，捕捉不到真身。
　　邀月公主等人，早已变色，这样的王曦未免太可怕了，一旦遇上，有几人可敌？！
　　“轰！”
　　突然，石昊浑身发光，体内至尊血液复苏，一下子施展出三种宝术！
　　上苍、轮回，还有第三种未明的神通，可以加持前两种神通，让它们威力更盛，令自身神力愈发恐怖，此时三种宝术的符文在其体内的血液中纠缠着，叠加在一起，让他发出了最为刺目的光！
　　一刹那，光雨无尽，从他的肉身冲出，淹没此地，那种叠加在一起的宝术无处不在，席卷四方。







"""


async def run():
    load_dotenv()
    import langextract as lx

    # 1. 优化的综合提取提示模板
    combined_prompt = textwrap.dedent("""\
        请从下面的小说片段中同时提取人物实体信息和人物之间的关系。

========== 要求说明 ============
需要提取两类信息：

【人物实体】提取要点：
1. 姓名：人物的正式名称
2. 别名/称号：人物的其他称呼方式
3. 身份/职位：人物在故事中的身份或职位
4. 特征描述：人物的外貌、性格或能力特征

【人物关系】提取要点：
1. 关系主体：关系的两个参与者，必须是上述的人物实体
2. 关系类型：如家族、师徒、情感、势力等关系
3. 关系描述：关系的具体内容和表现形式
4. 关系方向：谁是关系的主动方/被动方

========== 输出格式 =========
[
    {
        "extraction_class": "character",
        "extraction_text": "人物名称",
        "attributes": {
            "alias": "别名或称号",
            "identity": "身份或职位",
            "features": "特征描述",
            "key_actions": "关键行为"
        }
    },
    {
        "extraction_class": "relationship",
        "extraction_text": "关系描述文本",
        "attributes": {
            "character_1": "关系主动方/发起方",
            "character_2": "关系被动方/接收方",
            "relation_type": "关系类型",
            "intensity": "关系强度(强/中/弱)",
            "context": "关系背景或补充说明"
        }
    }
]


============ 规则要求 ==============
1. 只提取文本中明确提及的信息，不要推测
2. 所有信息必须有原文依据
3. 如果某属性在文本中没有提及，则该属性留空
4. 每个实体在当前抽取的结果中只应该出现一次, 如果有别名,放在alias;如果有多个人物或关系，则分别输出多条数据
5. 如果实体有多个身份，放在identity
6. 对于模糊或不确定的信息，不要进行提取
7. 关系类型逻辑：`relation_type`（如"保护关系"）必须与角色身份匹配，相同或者语义接近的关系不需要重复提取，如战斗、敌对、对抗
8. attributes是属性 不是extraction_class
    """)

    # 2. 优化的综合提取示例
    combined_examples = [
        lx.data.ExampleData(
            text=textwrap.dedent("""\
            石云峰站在院子中央，手持古老的骨书，正在为小不点的洗礼仪式做准备。作为族长，他对石昊寄予厚望，希望这个天资聪颖的孩子能够超越超级大族的天才。
            "小不点虽然年幼，但潜力无穷，不能浪费了他的天赋。"石云峰自语道。
            石昊，人称小不点，只有五岁，却已经展现出非凡的悟性，是村中最有希望的少年。"""),
            extractions=[
                # 人物提取示例
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="石云峰",
                    attributes={
                        "alias": "族长",
                        "identity": "族长",
                        "features": "手持古老的骨书",
                        "key_actions": "为小不点的洗礼仪式做准备"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="石昊",
                    attributes={
                        "alias": "小不点",
                        "identity": "村中少年",
                        "features": "天资聪颖，潜力无穷，展现出非凡的悟性",
                        "key_actions": "即将接受五岁洗礼"
                    }
                ),
                # 关系提取示例
                lx.data.Extraction(
                    extraction_class="relationship",
                    extraction_text="他对石昊寄予厚望，希望这个天资聪颖的孩子能够超越超级大族的天才",
                    attributes={
                        "character_1": "石云峰",
                        "character_2": "石昊",
                        "relation_type": "长辈关系",
                        "intensity": "强",
                        "context": "族长对有天赋少年的期望和培养"
                    }
                )
            ]
        ),
        # 添加第二个更复杂的示例
        lx.data.ExampleData(
            text=textwrap.dedent("""\
            "师父，这次试炼我一定不会让您失望的！"林天恭敬地对着李青山行礼道。
            李青山抚须微笑，看着自己最得意的弟子，眼中满是欣慰。"为师相信你，不过要小心那魔教妖女苏妍，她武功诡异，心思难测。"
            "是，弟子谨记师父教诲。"林天点头应道，眼神中却闪过一丝复杂的神色。
            其实林天与苏妍早已暗中相识，两人惺惺相惜，只是碍于门派之争，不得不隐瞒这段情谊。"""),
            extractions=[
                # 人物提取
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="林天",
                    attributes={
                        "alias": "弟子",
                        "identity": "李青山的弟子",
                        "features": "恭敬，眼神中闪过复杂神色",
                        "key_actions": "向师父行礼，暗中与苏妍相识"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="李青山",
                    attributes={
                        "alias": "",
                        "identity": "师父",
                        "features": "抚须微笑，眼中满是欣慰",
                        "key_actions": "告诫弟子小心魔教妖女"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="苏妍",
                    attributes={
                        "alias": "魔教妖女",
                        "identity": "魔教成员",
                        "features": "武功诡异，心思难测",
                        "key_actions": "与林天暗中相识"
                    }
                ),
                # 关系提取
                lx.data.Extraction(
                    extraction_class="relationship",
                    extraction_text="林天恭敬地对着李青山行礼道",
                    attributes={
                        "character_1": "林天",
                        "character_2": "李青山",
                        "relation_type": "师徒关系",
                        "intensity": "强",
                        "context": "弟子对师父的尊敬"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="relationship",
                    extraction_text="林天与苏妍早已暗中相识，两人惺惺相惜",
                    attributes={
                        "character_1": "林天",
                        "character_2": "苏妍",
                        "relation_type": "情感关系",
                        "intensity": "中",
                        "context": "门派之争下的秘密情谊"
                    }
                )
            ]
        )
    ]

    # 3. 执行综合提取
    print("🧙 开始提取人物和关系信息...")
    combined_result = lx.extract(
        text_or_documents=NOVEL_DEMO,
        prompt_description=combined_prompt,
        examples=combined_examples,
        config=ModelConfig(
            model_id=os.environ.get("LLM_MODEL"),
            provider="openai",
            provider_kwargs={
                "api_key": os.environ.get('LLM_API_KEY'),
                "base_url": os.environ.get("LLM_BASE_URL"),
            }
        ),
        fence_output=False,
        use_schema_constraints=False
    )

    # 4. 保存结果到JSONL文件
    lx.io.save_annotated_documents([combined_result], output_name="novel_extraction_results.jsonl", output_dir=".")
    # 5. 生成可视化
    html_content = lx.visualize("novel_extraction_results.jsonl")
    html_content = f"<html><meta charset='UTF-8'/>{html_content}</html>"
    with open("visualization.html", "w") as f:
        if hasattr(html_content, 'data'):
            f.write(html_content.data)  # For Jupyter/Colab
        else:
            f.write(html_content)




    print("✅ 提取完成！结果已保存到文件")

    # 6. 分类输出结果
    characters = []
    relationships = []

    for extraction in combined_result.extractions:
        if extraction.extraction_class == "character":
            characters.append(extraction)
        elif extraction.extraction_class == "relationship":
            relationships.append(extraction)

    print(f"📊 提取结果统计：找到 {len(characters)} 个人物和 {len(relationships)} 个关系")

    # 7. 打印部分结果示例
    if characters:
        print("\n🧑 人物示例:")
        for i, char in enumerate(characters[:20], 1):  # 只显示前两个
            print(f"  {i}. {char.extraction_text} - {char.attributes.get('identity', '未知身份')}")

    if relationships:
        print("\n🔗 关系示例:")
        for i, rel in enumerate(relationships[:20], 1):  # 只显示前两个
            print(f"  {i}. {rel.attributes.get('character_1', '?')} 与 {rel.attributes.get('character_2', '?')} - {rel.attributes.get('relation_type', '未知关系')}")


if __name__ == '__main__':
    asyncio.run(run())
