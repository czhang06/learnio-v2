from app.config import settings
from app.services import segmenter

LONG_A = "Explain the difference between a stack and a queue in detail."
LONG_B = "Describe how binary search works and state its complexity."
LONG_C = "Prove that the sum of two even integers is always even."


def test_split_dot_style():
    raw = f"1. {LONG_A}\n2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_split_paren_style():
    raw = f"1) {LONG_A}\n2) {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_split_question_n_style():
    raw = f"Question 1: {LONG_A}\nQuestion 2: {LONG_B}\nquestion 3: {LONG_C}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B, LONG_C]


def test_split_normalizes_whitespace_in_multiline_question():
    raw = "1. Explain the difference\n   between a stack\n   and a queue.\n2. " + LONG_B
    result = segmenter.split_questions(raw)
    assert result[0] == "Explain the difference between a stack and a queue."
    assert result[1] == LONG_B


def test_short_fragments_are_dropped():
    raw = f"1. Too short.\n2. {LONG_A}\n3. Also tiny\n"
    assert segmenter.split_questions(raw) == [LONG_A]


def test_no_questions_returns_empty_list():
    assert segmenter.split_questions("Just a paragraph with no numbering at all.") == []
    assert segmenter.split_questions("") == []


def test_text_before_first_question_is_ignored():
    raw = f"Midterm exam, Spring term. Answer everything.\n1. {LONG_A}\n"
    assert segmenter.split_questions(raw) == [LONG_A]


# The cases below mirror the structure of a real exam that parsed to zero
# questions: headings with mark annotations, a question opening a new page,
# a year in the header, and a sign-off after the last question.


def test_split_keyword_heading_with_mark_annotation():
    raw = f"Question 1 (9 points)\n{LONG_A}\nQuestion 2 (11 points)\n{LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(9 points) {LONG_A}", f"(11 points) {LONG_B}"]


def test_split_problem_keyword_without_separator():
    raw = f"Problem 1\n{LONG_A}\nPROBLEM 2\n{LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_split_bare_number_with_mark_count():
    raw = f"1 (10 marks) {LONG_A}\n2 [5 marks] {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(10 marks) {LONG_A}", f"[5 marks] {LONG_B}"]


def test_split_question_starting_a_new_page():
    raw = f"Question 1 (9 points)\n{LONG_A}\fQuestion 2 (11 points)\n{LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(9 points) {LONG_A}", f"(11 points) {LONG_B}"]


def test_split_numbered_question_after_page_break_and_newline():
    raw = f"1. {LONG_A}\n\f 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_year_in_header_does_not_start_a_question():
    raw = f"Midterm Examination\n2004 Winter Term 1, 50 minutes in total\n1. {LONG_A}\n"
    assert segmenter.split_questions(raw) == [LONG_A]


def test_trailing_sign_off_is_stripped():
    raw = f"1. {LONG_A}\n2. {LONG_B}\n\n--- The End ---\nGood luck!\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]
    assert segmenter.split_questions("1. Walk the linked list from the head to the end.") == [
        "Walk the linked list from the head to the end."
    ]


def test_normalize_collapses_whitespace():
    assert segmenter.normalize("  a \n\t b   c  ") == "a b c"


def test_text_hash_ignores_case_and_whitespace():
    assert segmenter.text_hash("What  is\nRecursion?") == segmenter.text_hash("  what is recursion? ")


def test_text_hash_differs_for_different_text():
    assert segmenter.text_hash("what is recursion?") != segmenter.text_hash("what is iteration?")


def test_text_hash_is_sha256_hex():
    h = segmenter.text_hash("x")
    assert len(h) == 64
    int(h, 16)


def test_tag_topics_by_keyword_is_case_insensitive():
    topics = ["Recursion", "graphs", "sorting"]
    assert segmenter.tag_topics_by_keyword("Use RECURSION on GRAPHS", topics) == [
        "Recursion",
        "graphs",
    ]


def test_tag_topics_by_keyword_no_match():
    assert segmenter.tag_topics_by_keyword("What is a hash map?", ["graphs"]) == []


def test_llm_tagging_falls_back_to_keywords_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    questions = ["Explain recursion with an example.", "Define a graph traversal."]
    labels = segmenter.tag_topics_with_llm(questions, ["recursion", "graph"])
    assert labels == [["recursion"], ["graph"]]


def test_llm_tagging_without_topics_returns_empty_labels(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-key")
    assert segmenter.tag_topics_with_llm(["a question", "another"], []) == [[], []]
