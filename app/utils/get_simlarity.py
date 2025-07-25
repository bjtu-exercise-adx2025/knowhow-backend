import json

from sklearn.metrics.pairwise import cosine_similarity

from .llm_service import embedding_qwen_v4_list


def cosine_similarity_list_sbert(text1, text_list, batch_size=10):
    """
    使用qwen embedding计算一段文本与多段文本的余弦相似度（批处理版本）

    Args:
        text1: 要比较的文本
        text_list: 多段文本列表
        batch_size: 批处理大小

    Returns:
        list: 每段文本与text1的余弦相似度值列表 (-1到1之间)
    """
    # 先获取text1的embedding
    text1_response = embedding_qwen_v4_list([text1])
    text1_data = json.loads(text1_response)
    text1_embedding = text1_data['data'][0]['embedding']

    all_similarities = []

    # 分批处理text_list
    for i in range(0, len(text_list), batch_size):
        batch_texts = text_list[i:i + batch_size]

        # 获取当前批次的embeddings
        batch_response = embedding_qwen_v4_list(batch_texts)
        batch_data = json.loads(batch_response)
        batch_embeddings = [item['embedding'] for item in batch_data['data']]

        # 计算当前批次的相似度
        batch_similarities = cosine_similarity([text1_embedding], batch_embeddings)[0]
        all_similarities.extend(batch_similarities.tolist())

    return all_similarities


def cosine_similarity_sbert(text1, text2):
    """
    使用sentence-transformers计算两段文本的余弦相似度

    Args:
        text1, text2: 要比较的两段文本
        model_name: 预训练模型名称

    Returns:
        float: 余弦相似度值 (-1到1之间)
    """
    # 获取两段文本的embedding并解析JSON
    embeddings_response = embedding_qwen_v4_list([text1, text2])
    embeddings_data = json.loads(embeddings_response)
    embeddings = [item['embedding'] for item in embeddings_data['data']]

    # 计算余弦相似度
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

    return similarity


# 测试文本
texts = {
    "相关文本A": """# 北京交通大学简介
北京交通大学创建于1896年，是中国第一所专门培养管理人才的高等学校，现为211工程、985工程优势学科创新平台和双一流建设高校。
## 特色与优势
学校以交通运输工程、信息与通信工程、系统科学等学科为特色优势，在轨道交通、智能交通、信息通信等领域具有突出的科研实力和人才培养优势。
## 历史声誉
北京交通大学素有“中国铁路工程师摇篮”之称，为国家交通事业和信息技术发展培养了大批高层次专门人才。""",

    "相关文本B": """shanghai Jiaotong University will moved to XiongAn""",

    "无关文本C": """古代丝绸之路是连接东西方文明的重要贸易通道，它不仅促进了商品的流通，更重要的是推动了不同文化之间的交流与融合。从长安出发，商队载着丝绸、茶叶、瓷器等中国特产，穿越戈壁沙漠，经过河西走廊，到达中亚、西亚乃至欧洲。这条路线上的每一个驿站都见证了东西方商人的足迹，也记录了文化传播的历史轨迹。佛教沿着丝绸之路从印度传入中国，而中国的造纸术、印刷术等发明也通过这条路径传播到世界各地。丝绸之路上的城市如撒马尔罕、布哈拉等都因贸易而繁荣，成为多元文化汇聚的中心。艺术风格、建筑技法、音乐形式在这条路上相互影响，形成了独特的丝路文化。今天，随着"一带一路"倡议的提出，古老的丝绸之路再次焕发出新的活力，成为促进国际合作与文明互鉴的重要纽带。""",

    "无关文本D": """海洋生物的多样性令人叹为观止，从微小的浮游生物到庞大的蓝鲸，海洋中孕育着地球上最丰富的生命形式。珊瑚礁被誉为海洋中的热带雨林，为无数海洋生物提供栖息地和食物来源。色彩斑斓的热带鱼类在珊瑚丛中穿梭，海龟慢悠悠地游过，而鲨鱼作为海洋食物链的顶端捕食者，维持着海洋生态系统的平衡。深海中生活着许多奇特的生物，它们适应了高压、低温、无光的极端环境，发展出了独特的生存策略，如生物发光、巨大化等特征。海洋不仅是生物的家园，也是地球气候系统的重要调节器，海水的蒸发和洋流的运动影响着全球的天气模式。然而，海洋污染、过度捕捞、气候变化等人类活动正在威胁着海洋生态系统的健康。保护海洋环境、维护海洋生物多样性已成为人类面临的重要挑战，需要全球共同努力来应对这一危机。"""
}


# 测试相似度计算
def test_similarity():
    print("=== 文本相似度测试 ===\n")

    sim_relateds = cosine_similarity_list_sbert_batch(
        texts["相关文本A"], [texts["相关文本B"], texts["无关文本C"], texts["无关文本D"]]
    )

    print(f"相关文本A vs 相关文本B: {sim_relateds[0]:.4f}")
    print(f"相关文本A vs 无关文本C: {sim_relateds[1]:.4f}")
    print(f"相关文本A vs 无关文本D: {sim_relateds[2]:.4f}\n")

    # # 测试相关文本
    # sim_related = cosine_similarity_sbert(
    #     texts["相关文本A"], texts["相关文本B"]
    # )
    # print(f"相关文本A vs 相关文本B: {sim_related:.4f}")
    #
    # # 测试无关文本
    # sim_unrelated = cosine_similarity_sbert(
    #     texts["无关文本C"], texts["无关文本D"]
    # )
    # print(f"无关文本C vs 无关文本D: {sim_unrelated:.4f}")
    #
    # # 交叉测试
    # sim_cross1 = cosine_similarity_sbert(
    #     texts["相关文本A"], texts["无关文本C"]
    # )
    # print(f"相关文本A vs 无关文本C: {sim_cross1:.4f}")
    #
    # sim_cross2 = cosine_similarity_sbert(
    #     texts["相关文本B"], texts["无关文本D"]
    # )
    # print(f"相关文本B vs 无关文本D: {sim_cross2:.4f}")


# 运行测试
if __name__ == "__main__":
    test_similarity()
