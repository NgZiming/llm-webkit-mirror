from typing import List, Tuple

from overrides import override

from llm_web_kit.extractor.html.recognizer.recognizer import \
    BaseHTMLElementRecognizer


class VideoRecognizer(BaseHTMLElementRecognizer):
    """解析视元素."""
    @override
    def recognize(self, base_url:str, main_html_lst: List[Tuple[str,str]], raw_html:str) -> List[Tuple[str,str]]:
        """父类，解析视频元素.

        Args:
            base_url: str: 基础url
            main_html_lst: main_html在一层一层的识别过程中，被逐步分解成不同的元素
            raw_html: 原始完整的html

        Returns:
        """
        raise NotImplementedError

    @override
    def to_content_list_node(self, base_url: str, parsed_content: str, raw_html_segment: str) -> dict:
        raise NotImplementedError
