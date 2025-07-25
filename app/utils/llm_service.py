from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="sk-bf463977dac346128403e5b44e76819b",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def llm_call_qwen3_8b(user_content: str, system_content: str = None) -> str:
    """
    调用LLM模型进行文本生成
    :param content: 用户输入的文本内容
    :return: LLM模型生成的文本结果
    """
    if system_content is None:
        system_content = "你是一个智能助手，能够回答用户的问题并提供相关信息。"
    completion = client.chat.completions.create(
        model="qwen3-8b",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        extra_body={"enable_thinking": False},  # 控制思考过程
    )
    return completion.choices[0].message.content

def embedding_qwen_v4(text: str) -> list:
    """
    使用Qwen V4模型生成文本的嵌入向量
    :param text: 输入文本
    :return: 文本的嵌入向量
    """
    completion = client.embeddings.create(
        model="text-embedding-v4",
        input='衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买',
        dimensions=1024,  # 指定向量维度（仅 text-embedding-v3及 text-embedding-v4支持该参数）
        encoding_format="float"
    )
    return completion.model_dump_json()

def embedding_qwen_v4_list(texts: list) -> list:
    """
    使用Qwen V4模型批量生成文本的嵌入向量
    :param texts: 输入文本列表
    :return: 文本的嵌入向量列表
    """
    completion = client.embeddings.create(
        model="text-embedding-v4",
        input=texts,
        dimensions=1024,  # 指定向量维度（仅 text-embedding-v3及 text-embedding-v4支持该参数）
        encoding_format="float"
    )
    return completion.model_dump_json()


if __name__ == "__main__":
    # # 测试LLM调用
    # test_content = "你好，今天的天气怎么样？"
    # response = llm_call_qwen3_8b(test_content)
    # print("LLM Response:", response)

    # 测试嵌入向量生成
    test_text = "衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买"
    embedding = embedding_qwen_v4(test_text)
    print("Embedding for single text:", embedding)
    print("Embedding shape:", len(embedding))
    # 测试批量嵌入向量生成
    test_texts = [
        "衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买",
        "这件衣服的颜色很正，穿上去很有气质，值得购买！",
        "质量一般，和描述不符，有点失望。",
        "非常满意，物流也很快，下次还会再来！"
    ]
    embeddings = embedding_qwen_v4_list(test_texts)
    print("Embeddings for multiple texts:", embeddings)
    print("Embeddings shape:", len(embeddings))
