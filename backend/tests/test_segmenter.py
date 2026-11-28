from app.config import settings
from app.ingest import segmenter

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


def test_split_keeps_line_breaks_and_undoes_hanging_indent():
    raw = "1. Explain the difference\n   between a stack\n   and a queue.\n2. " + LONG_B
    result = segmenter.split_questions(raw)
    assert result[0] == "Explain the difference\nbetween a stack\nand a queue."
    assert result[1] == LONG_B


def test_split_keeps_indentation_of_code_and_sub_parts():
    raw = (
        "1. Consider this table definition:\n"
        "\n"
        "      CREATE TABLE t\n"
        "            (a INT,\n"
        "            b INT)\n"
        "\n\n\n"
        "   a) Name the key.\n"
        "   b) Name a dependency.\n"
        f"2. {LONG_B}\n"
    )
    assert segmenter.split_questions(raw)[0] == (
        "Consider this table definition:\n"
        "\n"
        "   CREATE TABLE t\n"
        "         (a INT,\n"
        "         b INT)\n"
        "\n"
        "a) Name the key.\n"
        "b) Name a dependency."
    )


def test_code_after_a_single_prose_line_stays_indented():
    raw = "1. What does this statement return?\n       select count(*)\n       from donations\n"
    assert segmenter.split_questions(raw) == [
        "What does this statement return?\n    select count(*)\n    from donations"
    ]


def test_short_check_ignores_layout_whitespace():
    raw = f"1. Tiny\n\n\n            one\n2. {LONG_A}\n"
    assert segmenter.split_questions(raw) == [LONG_A]


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
    assert segmenter.split_questions(raw) == [f"(9 points)\n{LONG_A}", f"(11 points)\n{LONG_B}"]


def test_split_problem_keyword_without_separator():
    raw = f"Problem 1\n{LONG_A}\nPROBLEM 2\n{LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_split_bare_number_with_mark_count():
    raw = f"1 (10 marks) {LONG_A}\n2 [5 marks] {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(10 marks) {LONG_A}", f"[5 marks] {LONG_B}"]


def test_split_question_starting_a_new_page():
    raw = f"Question 1 (9 points)\n{LONG_A}\fQuestion 2 (11 points)\n{LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(9 points)\n{LONG_A}", f"(11 points)\n{LONG_B}"]


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


# Formats seen in real past exams: marks printed in the margin before the
# question number, a numbered rules page before the first question, and a
# running footer on every page. The text here is synthetic.


def test_split_marks_in_parentheses_before_the_number():
    raw = f"(10 points) 1. {LONG_A}\n(12 points) 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(10 points) {LONG_A}", f"(12 points) {LONG_B}"]


def test_split_bare_mark_count_before_the_number():
    raw = f"15 marks 1. {LONG_A}\n 8 marks 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"(15 marks) {LONG_A}", f"(8 marks) {LONG_B}"]


def test_split_bracketed_count_before_the_number_is_kept_as_printed():
    raw = f"[9] 1. {LONG_A}\n[12] 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"[9] {LONG_A}", f"[12] {LONG_B}"]


def test_numbered_exam_rules_are_not_questions():
    raw = (
        "Rules for formal examinations\n"
        "1. Each candidate must show a library card to the invigilator when asked.\n"
        "2. No candidate may enter the examination room after the first half hour.\n"
        "3. Candidates must not take any examination material out of the room.\n"
        f"(10 marks) 1. {LONG_A}\n"
    )
    assert segmenter.split_questions(raw) == [f"(10 marks) {LONG_A}"]


def test_numbered_instructions_are_not_questions_even_with_non_breaking_spaces():
    raw = "1. Answer\xa0all\xa0the\xa0questions\xa0on\xa0this\xa0paper.\n2. Use point form where it helps.\n" + f"3. {LONG_A}\n"
    assert segmenter.split_questions(raw) == [LONG_A]


def test_marked_question_that_mentions_candidates_is_kept():
    text = "(5 marks) A candidate key must be minimal. Explain why examiners of a schema care."
    assert segmenter.split_questions("1. " + text) == [text]


def test_page_footers_are_removed_from_question_text():
    raw = f"1. {LONG_A}\n   2015-12-18 MATH 302 Page 3 of 12\n2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_clean_layout_treats_a_page_break_as_a_line_break():
    assert segmenter.clean_layout("first line\fsecond line\n") == "first line\nsecond line"


def test_layout_does_not_change_the_dedup_hash():
    flat = "Explain the difference between a stack and a queue."
    laid_out = segmenter.clean_layout("Explain the difference\n   between a stack\n\n   and a queue.")
    assert "\n" in laid_out
    assert segmenter.text_hash(laid_out) == segmenter.text_hash(flat)


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


# Choosing which numbered lines are questions. Questions are numbered 1, 2, 3...
# and lists inside a question restart, so the longest such run wins.


def test_numbered_list_inside_a_question_does_not_split_it():
    raw = (
        f"Problem 1. {LONG_A}\n"
        "   1. MARK(i): mark element i as important.\n"
        "   2. NEXT(i): find the next marked element after i.\n"
        f"Problem 2. {LONG_B}\n"
    )
    first, second = segmenter.split_questions(raw)
    assert "MARK(i)" in first and "NEXT(i)" in first
    assert second == LONG_B


def test_multiple_choice_options_do_not_split_a_numbered_question():
    raw = (
        f"1. {LONG_A}\n"
        "     1. A stack is first in, first out\n"
        "     2. A queue is first in, first out\n"
        "     3. None of the above\n"
        f"2. {LONG_B}\n"
        f"3. {LONG_C}\n"
    )
    questions = segmenter.split_questions(raw)
    assert len(questions) == 3
    assert "None of the above" in questions[0]


def test_two_level_quiz_headings():
    raw = (
        f"Quiz 1, Question 1, Rules (50 points)\n{LONG_A}\n"
        f"Quiz 1, Question 2, Search (50 points)\n{LONG_B}\n"
        f"Quiz 2, Problem 1, (25 points)\n{LONG_C}\n"
    )
    questions = segmenter.split_questions(raw)
    assert [q.split("\n")[-1] for q in questions] == [LONG_A, LONG_B, LONG_C]
    assert questions[0].startswith("Rules (50 points)")


def test_number_then_keyword_heading():
    assert segmenter.split_questions(f"1 Team Problem: A Mystery\n{LONG_A}\n") == [f"A Mystery\n{LONG_A}"]


def test_cover_grid_numbers_on_the_line_before_question_one():
    raw = (
        "Your PRINTED name is: 1.\n"
        "                                         2.\n"
        "                                         3.\n"
        f" 1. (12 points) {LONG_A}\n"
        f" 2. (11 points) {LONG_B}\n"
        f" 3. (11 points) {LONG_C}\n"
    )
    assert [q[q.index(")") + 2 :] for q in segmenter.split_questions(raw)] == [LONG_A, LONG_B, LONG_C]


def test_repeated_answer_pages_are_not_new_questions():
    raw = (
        f"Problem 1: {LONG_A}\nProblem 2: {LONG_B}\n"
        "Each question is repeated in the following pages.\n"
        f"Problem 1: {LONG_A}\nProblem 2: {LONG_B}\n"
    )
    assert segmenter.split_questions(raw) == [LONG_A, f"{LONG_B}\nEach question is repeated in the following pages."]


def test_tear_off_sheet_labels_are_not_questions():
    raw = (
        f"Problem 1: {LONG_A}\nProblem 2: {LONG_B}\n"
        "Tear off sheet\nProblem 1, Part B\nTear off sheet\nProblem 2, Part B\n"
    )
    questions = segmenter.split_questions(raw)
    assert questions[0] == LONG_A and questions[1].startswith(LONG_B) and len(questions) == 2


def test_a_second_section_with_its_own_numbering_is_kept():
    long_d = "Show that every tree with n vertices has exactly n minus one edges."
    raw = f"Part A\n1. {LONG_A}\n2. {LONG_B}\nPart B\n1. {LONG_C}\n2. {long_d}\n"
    assert segmenter.split_questions(raw) == [LONG_A, f"{LONG_B}\nPart B", LONG_C, long_d]


def test_write_your_name_item_is_not_a_question_even_with_points():
    raw = (
        "Problem 1. [2 points] Information\n"
        "(a) [1 point] Write your name at the top of each page.\n"
        f"Problem 2. {LONG_A}\n"
    )
    assert segmenter.split_questions(raw) == [LONG_A]


def test_dagger_marked_extra_problem_is_its_own_question():
    raw = f"1. {LONG_A}\n2. {LONG_B}\nG1† . {LONG_C}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B, LONG_C]


def test_only_dagger_problems():
    assert segmenter.split_questions(f"G1† . {LONG_A}\n") == [LONG_A]


def test_heading_numbers_follow_each_other():
    assert segmenter._follows((1,), (2,))
    assert not segmenter._follows((1,), (3,))
    assert segmenter._follows((1, 2), (1, 3))
    assert segmenter._follows((1, 2), (2, 1))
    assert not segmenter._follows((1, 2), (3, 1))
    assert not segmenter._follows((1,), (1, 2))


def test_bulleted_keyword_heading():
    raw = f"   • Question 1. {LONG_A}\n   • Question 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]


def test_numbered_title_headings():
    raw = f" 1 The L-tower problem\n {LONG_A}\n 2 Double Sums\n {LONG_B}\n"
    assert segmenter.split_questions(raw) == [f"The L-tower problem\n{LONG_A}", f"Double Sums\n{LONG_B}"]


def test_table_rows_ending_in_numbers_are_not_titles():
    raw = f" 1 True or False 40 10\n 2 Fast Fourier Transform 5 1\nProblem 1. {LONG_A}\nProblem 2. {LONG_B}\n"
    assert segmenter.split_questions(raw) == [LONG_A, LONG_B]
