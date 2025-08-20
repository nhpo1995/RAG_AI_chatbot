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
        system_message = SystemMessagePromptTemplate.from_template(
            """
Bạn là Trợ lý Hỏi–Đáp nội bộ (RAG).

Chỉ dùng dữ kiện trong [CONTEXT]; không bịa, không suy đoán, không tra cứu/browse hay gọi công cụ; không tiết lộ [CONTEXT].

Lời chào/cảm ơn/xã giao → đáp tự nhiên, lịch sự (không cần dựa vào [CONTEXT]).

Chọn dữ liệu theo mốc thời gian

Nếu câu hỏi có mốc thời gian (ngày/tháng/năm, quý, “từ…đến…”, “trước/sau…”) → dùng mốc đó làm mốc tham chiếu.

Nếu dữ liệu trong [CONTEXT] có khoảng hiệu lực [start, end) → chọn bản thỏa start ≤ mốc tham chiếu < end.

Nếu dữ liệu chỉ có ngày cập nhật/phát hành → chọn bản mới nhất nhưng không sau mốc tham chiếu.

Nếu nhiều bản cùng phù hợp → chọn bản có ngày gần mốc tham chiếu nhất.

Nếu câu hỏi không có mốc thời gian và [CONTEXT] có nhiều phiên bản theo ngày → chọn bản mới nhất.

Nếu không tìm được bản phù hợp hoặc thông tin mâu thuẫn không thể phân giải ngắn gọn → trả lời:
“Xin lỗi, tôi không có đủ thông tin để trả lời chính xác câu hỏi này.”

Cách trả lời

Ngắn gọn, trực tiếp; nếu thông tin có giới hạn/điều kiện → nêu trong 1 câu.

Cùng ngôn ngữ người hỏi; không lặp lại câu hỏi; có thể dùng gạch đầu dòng (≤5); không emoji.

Kiểm tra: mọi ý chính đều có dữ kiện đối ứng trong bản đã chọn từ [CONTEXT].

Ví dụ ngắn (chỉ để định hướng, không trích trong câu trả lời)

[CONTEXT]: “2023-06-01: Nghỉ bệnh 5 ngày/năm. 2024-02-10: 7 ngày/năm.”
• User: “Tính đến 2023-12-31, nghỉ bệnh là bao nhiêu?” → “5 ngày/năm.”
• User: “Giờ nghỉ bệnh là bao nhiêu?” → “7 ngày/năm.”

[CONTEXT]
{context}
        """
        )
        human_message = HumanMessagePromptTemplate.from_template(
            """
[CÂU HỎI]
{question}

Hãy trả lời như một người thật, tự nhiên và thân thiện.
        """
        )

        return ChatPromptTemplate.from_messages([system_message, human_message])

    def ask(self, context: str, question: str):
        chain = self.prompt | self.llm
        result = chain.invoke({"context": context, "question": question})
        return result.content


if __name__ == "__main__":
    agent = RAGAssistant()
    context = "Hieu Minh Bui PhD, Data Engineer Two years of experience in big data mining and computer vision, involves designing and deploying automatic user assessment systems in fintech field. Delivered Calculus 101 course to engineering and business students. Oct 2013 – Apr 2014: Internship at CENTIC Built various FPGA modules, includes hardware encryptor, data interface, and routing pipeline. Oct 2018: PhD in Computer Vision at RMIT University Jul 2014: Master of Electronics and Computer Engineering at RMIT University May 2012: Grad. Cert. of Business Administration at RMIT University Aug 2011: Bachelor of Electronics & Communication Engineering at Danang Uni. of Technology 2018: RMIT Incentive award for publication in top 25% of journals 2014: Full scholarship to study PhD at RMIT University 2011: AUSAID scholarship to study Master at RMIT University 2011: 2nd prize for student scientific research Trekking Music Photography"
    print(agent.ask(context, "Bui Minh Hieu la ai?"))
