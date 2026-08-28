import unittest
from xml.etree import ElementTree

from main import render_faq_document


class FaqRenderingTests(unittest.TestCase):
    def test_level_two_headings_render_as_closed_accordion_items(self):
        rendered = render_faq_document("faq.md")
        root = ElementTree.fromstring(f"<root>{rendered}</root>")
        questions = root.findall("details")

        self.assertGreater(len(questions), 0)
        self.assertEqual(root.find("h1").text, "Frequently Asked Questions")
        self.assertIsNone(root.find("h2"))

        for question in questions:
            self.assertEqual(question.attrib["class"], "faq-item")
            self.assertEqual(question.attrib["name"], "faq")
            self.assertNotIn("open", question.attrib)
            self.assertIsNotNone(question.find("summary/h2"))
            self.assertIsNotNone(question.find("div[@class='faq-answer']"))

    def test_subheadings_remain_inside_their_question_answer(self):
        rendered = render_faq_document("faq.md")
        root = ElementTree.fromstring(f"<root>{rendered}</root>")
        first_answer = root.find("details/div[@class='faq-answer']")

        self.assertIsNotNone(first_answer.find("h3"))


if __name__ == "__main__":
    unittest.main()
