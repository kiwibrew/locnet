import unittest
from xml.etree import ElementTree

from markdown import markdown

from app.main import FaqAccordionExtension, render_faq_document


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
        markdown_source = """# Frequently Asked Questions

## Example question

Example answer.

### Example subheading

More answer content.
"""
        rendered = markdown(
            markdown_source,
            extensions=[FaqAccordionExtension()],
        )
        root = ElementTree.fromstring(f"<root>{rendered}</root>")
        question = root.find("details")
        answer = question.find("div[@class='faq-answer']")
        subheading = answer.find("h3")

        self.assertEqual(question.find("summary/h2").text, "Example question")
        self.assertIsNotNone(subheading)
        self.assertEqual(subheading.text, "Example subheading")


if __name__ == "__main__":
    unittest.main()
