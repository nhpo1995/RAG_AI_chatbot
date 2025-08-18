from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from utils.logger import setup_colored_logger
import config

setup_colored_logger()
load_dotenv()

class RAGAssistant:
    def __init__(self, model_name: str = config.LLM_MODEL, temperature: float = 0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = self._build_prompt()

    def _build_prompt(self):
        system_message = SystemMessagePromptTemplate.from_template("""
Bạn là một trợ lý ảo chuyên nghiệp. Trả lời câu hỏi dựa trên thông tin trong [CONTEXT] dưới đây.

Hướng dẫn:
- Chỉ sử dụng thông tin từ [CONTEXT], không bịa kiến thức ngoài context.
- Có thể tóm tắt, diễn giải hoặc sắp xếp thông tin để trả lời tự nhiên và dễ hiểu.
- Nếu [CONTEXT] có bảng số liệu, hiển thị bảng đó bằng **Markdown**.
- Nếu [CONTEXT] có hình ảnh, hiển thị bằng Markdown:
  ![caption](filepath)
  Trong đó filepath có thể là URL hoặc base64 do hệ thống cung cấp.
- Nếu context không đủ chi tiết, vẫn trả lời dựa trên những gì có trong context và nhấn mạnh hạn chế nếu cần.
- Hiểu câu hỏi tiếng Việt có hoặc không dấu.
- Trả lời chuyên nghiệp, ngắn gọn, rõ ràng, không lặp lại câu hỏi.

[CONTEXT]
{context}
        """)

        human_message = HumanMessagePromptTemplate.from_template("""
[CÂU HỎI]
{question}

Hãy trả lời như một người thật, tự nhiên và thân thiện.
        """)

        return ChatPromptTemplate.from_messages([system_message, human_message])

    def ask(self, context: str, question: str) -> str:
        chain = self.prompt | self.llm
        result = chain.invoke({"context": context, "question": question})
        return result.content

if __name__ == "__main__":
    agent = RAGAssistant()
    context = "Hieu Minh Bui PhD, Data Engineer Two years of experience in big data mining and computer vision, involves designing and deploying automatic user assessment systems in fintech field. Delivered Calculus 101 course to engineering and business students. Oct 2013 – Apr 2014: Internship at CENTIC Built various FPGA modules, includes hardware encryptor, data interface, and routing pipeline. Oct 2018: PhD in Computer Vision at RMIT University Jul 2014: Master of Electronics and Computer Engineering at RMIT University May 2012: Grad. Cert. of Business Administration at RMIT University Aug 2011: Bachelor of Electronics & Communication Engineering at Danang Uni. of Technology 2018: RMIT Incentive award for publication in top 25% of journals 2014: Full scholarship to study PhD at RMIT University 2011: AUSAID scholarship to study Master at RMIT University 2011: 2nd prize for student scientific research Trekking Music Photography"
    print(agent.ask(context, "Bui Minh Hieu la ai?"))
