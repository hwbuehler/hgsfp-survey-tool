# This custom Python class is used to automate the analysis of the HGSFP Graduate Days survey.
# Optimized/refactored version of survey_analyzer.py by ChatGPT Codex
from __future__ import annotations

import io
import json
import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from fpdf import FontFace
from fpdf.enums import CellBordersLayout, TableCellFillMode

from pypdf import PdfReader, PdfWriter
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering


# Change: centralized repeated constants into a dataclass for clarity and reuse.
@dataclass(frozen=True)
class SurveyConstants:
    answ_keys: Tuple[str, ...] = (
        "interesting",
        "new",
        "expected",
        "exciting",
        "structure",
        "level",
        "comments",
    )
    labels: Tuple[str, ...] = (
        "strongly disagree",
        "disagree",
        "neutral",
        "agree",
        "strongly agree",
    )
    labels_level: Tuple[str, ...] = (
        "very difficult",
        "difficult",
        "balanced",
        "easy",
        "very easy",
    )
    answer_titles: Tuple[str, ...] = (
        "The content was interesting",
        "The content was new to me",
        "The content was as expected",
        "The content was exciting",
        "The course was well-structured",
        "The level of the course was",
    )
    # Change: extracted palette to a single constant for consistency.
    likert_palette: Tuple[str, ...] = (
        "#B2182B",
        "#EF8A62",
        "#D9D9D9",
        "#67A9CF",
        "#2166AC",
    )


class SurveyAnalyzer:
    def __init__(self, data_path: str | None = None, output_path: str | None = None) -> None:
        # Change: allow passing an explicit data path to make the class easier to reuse/test.
        self.data, self.overall_count = self._read_data(data_path)
        self.path_out = os.path.join(output_path if output_path is not None else sys.argv[2], "")
        self.ml_titles, self.al_titles, self.il_title = self._determine_lecture_titles()
        self.constants = SurveyConstants()
        self.ml_results, self.al_results, self.il_results = self._initialize_results_list()
        self.overall_results = self._create_lecture_dictionary()
        self.overall_morning = self._create_lecture_dictionary()
        self.overall_afternoon = self._create_lecture_dictionary()
        self.organization: List[str] = []
        self.topics: List[str] = []
        self.dna_morning = 0
        self.dna_afternoon = 0
        self.dna_il = 0
        # Dictionaries containing mean and standard deviation for each question and lecture timeslot
        self.statistics = {}
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.MODEL_PATH = os.path.join(self.BASE_DIR, "models", "all-MiniLM-L6-v2")
        self.language_model = SentenceTransformer(self.MODEL_PATH)
        self.font_dir = os.path.join(self.BASE_DIR, "fonts")
        self._add_custom_fonts()

    def _add_custom_fonts(self):
        pdf = FPDF()
        pdf.add_font("dejavu-sans", style="", fname=os.path.join(self.font_dir, "DejaVuSans.ttf"))
        pdf.add_font("dejavu-sans", style="B", fname=os.path.join(self.font_dir, "DejaVuSans-Bold.ttf"))
        pdf.add_font("dejavu-sans", style="I", fname=os.path.join(self.font_dir, "DejaVuSans-Oblique.ttf"))
        pdf.add_font("dejavu-sans", style="BI", fname=os.path.join(self.font_dir, "DejaVuSans-BoldOblique.ttf"))
        self.pdf = pdf

    def _is_meaningful_comment(self, comment: str | None) -> bool:
        """Check if a comment is meaningful (not empty or just minimal characters)."""
        if comment is None:
            return False
        comment_stripped = comment.strip()
        if not comment_stripped:
            return False
        # Filter out comments that are just single punctuation characters
        if comment_stripped in (".", "-", ",", ";", ":", "?", "!"):
            return False
        return True

    def _segment_by_semantic_similarity(self, text, similarity_threshold: float = 0.0) -> List[str]:
        """
        Segment text into semantically distinct units using Sentence Transformer embeddings.

        Accepts either a plain string (split on sentence boundaries internally) or a
        pre-split list of parts (e.g. comma-separated topic suggestions). Adjacent parts
        are merged when their cosine similarity is at or above *similarity_threshold*, and
        kept as separate segments otherwise.

        Args:
            text: The text to segment, or a list of already-split candidate segments.
            similarity_threshold: Cosine-similarity cutoff (0-1). Parts whose similarity
                is *below* this value are treated as distinct segments.
                Default 0.0 (almost never splits a plain string).

        Returns:
            List of semantically distinct segments.
        """
        if isinstance(text, list):
            sentences = [s.strip() for s in text if s.strip()]
        else:
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return sentences
        
        # Get embeddings for all sentences
        embeddings = self.language_model.encode(sentences, convert_to_numpy=True)
        
        # Calculate similarity between adjacent sentences
        segments = []
        current_segment = sentences[0]
        
        for i in range(1, len(sentences)):
            # Cosine similarity
            similarity = np.dot(embeddings[i-1], embeddings[i]) / (
                np.linalg.norm(embeddings[i-1]) * np.linalg.norm(embeddings[i])
            )
            
            # If similarity is below threshold, start a new segment
            if similarity < similarity_threshold:
                segments.append(current_segment)
                current_segment = sentences[i]
            else:
                current_segment += " " + sentences[i]
        
        segments.append(current_segment)
        return segments

    def _append_answers(self, target: Dict[str, List], prefix: str, entry: Dict, comment_key: str | None = None) -> None:
        for key in self.constants.answ_keys[:-1]:
            target[key].append(entry[f"{prefix}{key}"])
        if comment_key and "sugg_lectures" in entry:
            # Check if the comment_key exists in sugg_lectures before accessing
            if comment_key in entry["sugg_lectures"]:
                comment = entry["sugg_lectures"][comment_key]
                # Only add meaningful comments; no semantic segmentation here —
                # lecture comments are full sentences and should not be split apart.
                if self._is_meaningful_comment(comment):
                    target["comments"].append(comment)

    def _read_data(self, data_path: str | None = None) -> Tuple[List[Dict],int]:
        """
        Load survey data from JSON file.

        Change: made the path parameter explicit and defaulted to sys.argv[1]
        to keep existing CLI behavior while improving reusability.
        """
        filepath = data_path if data_path is not None else sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            jfile = json.load(f)
            data_tmp = jfile["Data"]
            overall_count = jfile["ResultCount"]
        return data_tmp, overall_count

    def _determine_lecture_titles(self) -> Tuple[set[str], set[str], set[str]]:
        """
        Extract morning and afternoon lecture titles.
        """
        ml_titles_tmp = set()
        al_titles_tmp = set()
        il_title_tmp = set()
        for entry in self.data:
            if entry["ml_title"]!="DnA":
                ml_titles_tmp.add(entry["ml_title"])
            if entry["al_title"]!="DnA":
                al_titles_tmp.add(entry["al_title"])
            if entry["il_title"]!="DnA":
                il_title_tmp.add(entry["il_title"])
        return ml_titles_tmp, al_titles_tmp, il_title_tmp

    def _create_lecture_dictionary(self) -> Dict[str, List[int]]:
        """
        Create empty result dictionary for each lecture.
        """
        return {key: [] for key in self.constants.answ_keys}

    def _create_overall_results(self) -> None:
        # Change: avoid mutating keys and build the totals in a single pass.
        for question in self.constants.answ_keys[:-1]:
            combined: list[int] = []
            for title in self.ml_titles:
                combined.extend(self.ml_results[title][question])
            for title in self.al_titles:
                combined.extend(self.al_results[title][question])
            for title in self.il_title:
                combined.extend(self.il_results[title][question])
            self.overall_results[question] = combined
        self.overall_results.pop("comments", None)

    def _create_overall_morning(self):
        for question in self.constants.answ_keys[:-1]:
            combined: list[int] = []
            for lecture in self.ml_results.values():
                combined.extend(lecture[question])
            self.overall_morning[question]=combined
        self.overall_morning.pop("comments", None)

    def _create_overall_afternoon(self):
        for question in self.constants.answ_keys[:-1]:
            combined: list[int] = []
            for lecture in self.al_results.values():
                combined.extend(lecture[question])
            self.overall_afternoon[question]=combined
        self.overall_afternoon.pop("comments", None)

    def _initialize_results_list(self) -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, Dict]]:
        """
        Initialize lecture result dictionaries.
        """
        ml_results_tmp = {elem: self._create_lecture_dictionary() for elem in self.ml_titles}
        al_results_tmp = {elem: self._create_lecture_dictionary() for elem in self.al_titles}
        il_results_tmp = {elem:self._create_lecture_dictionary() for elem in self.il_title}
        return ml_results_tmp, al_results_tmp, il_results_tmp

    def _fill_results_list(self) -> None:
        """
        Populate the result dictionaries from the raw survey data.
        """
        for elem in self.data:
            ml_title_tmp = elem["ml_title"]
            al_title_tmp = elem["al_title"]
            il_title_tmp = elem["il_title"]

            # Handle morning lecture
            if ml_title_tmp == "DnA":
                self.dna_morning += 1
            else:
                self._append_answers(self.ml_results[ml_title_tmp], "ml_", elem, "ml_comment")
            
            # Handle afternoon lecture
            if al_title_tmp == "DnA":
                self.dna_afternoon += 1
            else:
                self._append_answers(self.al_results[al_title_tmp], "al_", elem, "al_comment")
            
            # Handle industry lecture
            if il_title_tmp == "DnA":
                self.dna_il += 1
            else:
                self._append_answers(self.il_results[il_title_tmp], "il_", elem, "il_comment")
            
            # Handle organization and topics suggestions
            if "sugg_organization" in elem:
                self.organization.append(elem["sugg_organization"])
            if "sugg_topics" in elem:
                self.topics.append(elem["sugg_topics"])
    
    def _change_pdf_font(self,pdf) -> None:
        pdf.add_font("dejavu-sans", style="", fname=os.path.join(self.BASE_DIR, "fonts", "DejaVuSans.ttf"))
        pdf.add_font("dejavu-sans", style="b", fname=os.path.join(self.BASE_DIR, "fonts", "DejaVuSans-Bold.ttf"))
        pdf.add_font("dejavu-sans", style="i", fname=os.path.join(self.BASE_DIR, "fonts", "DejaVuSans-Oblique.ttf"))
        pdf.add_font("dejavu-sans", style="bi", fname=os.path.join(self.BASE_DIR, "fonts", "DejaVuSans-BoldOblique.ttf"))

    # Adapted from author Sean Benoit, retrieved at 09/02/2026: Source - https://www.fpdf.org/en/script/script56.php
    def _create_comment_pdf(self, comments: List[str]) -> io.BytesIO:
        """
        Create a PDF page containing bullet list of comments.
        """
        pdf = FPDF(orientation="landscape")
        pdf.add_page()
        self._change_pdf_font(pdf)
        pdf.set_font("dejavu-sans", style="B", size=18)
        pdf.write(text="Comments \n\n")
        for txt in comments:
            if txt is None:
                continue
            pdf.set_font("zapfdingbats", size=8)
            pdf.cell(w=5, h=5, text="l ")
            pdf.set_font("dejavu-sans", size=11)
            pdf.multi_cell(w=0, h=5, text=txt)
            pdf.ln()
        page_output = io.BytesIO(pdf.output())
        return page_output

    # Based on ChatGPT Codex
    def _save_image_in_ram(self, fig) -> io.BytesIO:
        """
        Save matplotlib figure to an in-memory PNG.
        """
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        buf.seek(0)
        return buf

    def _labels_for_question(self, question: str) -> Tuple[str, ...]:
        return self.constants.labels_level if question == "level" else self.constants.labels

    def _calculate_lecture_statistics(self, results_dict: Dict[str, Dict[str, List[int]]]) -> None:
        """
        Calculate mean and standard deviation for all questions in each lecture.
        
        Only calculates statistics if the number of responses for a question exceeds 5.
        
        Args:
            results_dict: Dictionary with structure {lecture_title: {question: [answers]}}
        """
        for lecture_title, questions_dict in results_dict.items():
            # Use a dictionary to map questions to their stats for explicit ordering
            stats_dict = {}
            for question in self.constants.answ_keys[:-1]:
                results_arr = questions_dict[question]
                n = len(results_arr)
                if n > 5:
                    mean = float(np.mean(results_arr))
                    # Use ddof=1 for sample standard deviation (Bessel's correction)
                    std = float(np.std(results_arr, ddof=1))
                else:
                    mean = None
                    std = None
                stats_dict[question] = (mean, std)
            self.statistics[lecture_title] = stats_dict

    def _calculate_overall_statistics(self, results_dict: Dict[str, List[int]], key: str) -> None:
        """
        Calculate mean and standard deviation for a single overall results dictionary.
        
        Args:
            results_dict: Dictionary with structure {question: [answers]}
            key: Key to store statistics under (e.g., "Overall Results", "Overall Morning Lecture Results")
        """
        # Use a dictionary to map questions to their stats for explicit ordering
        stats_dict = {}
        for question in self.constants.answ_keys[:-1]:
            results_arr = results_dict[question]
            n = len(results_arr)
            if n > 5:
                mean = float(np.mean(results_arr))
                # Use ddof=1 for sample standard deviation (Bessel's correction)
                std = float(np.std(results_arr, ddof=1))
            else:
                mean = None
                std = None
            stats_dict[question] = (mean, std)
        self.statistics[key] = stats_dict


    # Depreceated, now displaying the mean and standard deviation directly under the horizontal bar plot using Matplotlib
    def _create_statistics_table_page(self, lecture_key: str) -> io.BytesIO:
        """Create a one-page PDF table of question means and standard deviations.

        The table has two rows:
        - Row 0: question numbers (1-6)
        - Row 1: mean ± std for the corresponding question

        Below the table we add a note about the Likert scale.
        """
        stats_dict = self.statistics.get(lecture_key)

        pdf_stats = FPDF(orientation="landscape")
        pdf_stats.add_page()
        self._change_pdf_font(pdf_stats)
        pdf_stats.set_font("dejavu-sans", style="B", size=18)
        pdf_stats.write(text="Question Statistics\n\n")

        # Two columns: Question label + Mean±Std value
        table_width = int(pdf_stats.w - 2 * pdf_stats.l_margin)
        col_widths = (int(table_width * 0.65), int(table_width * 0.35))

        headings_style = FontFace(emphasis="BOLD", color=255, fill_color=(255, 100, 0))
        with pdf_stats.table(
            borders_layout="NO_HORIZONTAL_LINES",
            cell_fill_color=(224, 235, 255),
            cell_fill_mode=TableCellFillMode.ROWS,
            col_widths=col_widths,
            headings_style=headings_style,
            line_height=8,
            text_align="LEFT",
            width=table_width,
        ) as table:
            # Header row (only row with a horizontal separator below it)
            row = table.row()
            row.cell("Question", border=CellBordersLayout.BOTTOM)
            row.cell("Mean ± Std", border=CellBordersLayout.BOTTOM)

            # Data rows: each question gets its own row
            for question_key in self.constants.answ_keys[:-1]:  # Excludes "comments"
                row = table.row()
                question_label = self.constants.answer_titles[self.constants.answ_keys[:-1].index(question_key)]
                row.cell(question_label, border=CellBordersLayout.NONE)
                
                if stats_dict is None or question_key not in stats_dict:
                    row.cell("N/A", border=CellBordersLayout.NONE)
                else:
                    mean, std = stats_dict[question_key]
                    if mean is None or std is None:
                        row.cell("N/A", border=CellBordersLayout.NONE)
                    else:
                        row.cell(f"{mean:.2f} ± {std:.2f}", border=CellBordersLayout.NONE)

        pdf_stats.ln(6)
        pdf_stats.set_font("dejavu-sans", size=10)
        pdf_stats.write(text="Likert rating scheme: 1 (most negative) to 5 (most positive).\n")

        return io.BytesIO(pdf_stats.output())

    def _create_likert_figure(self, results_dict: Dict[str, List[int]], title: str, lecture_key: str | None = None) -> io.BytesIO:
        # Landscape A4 in inches
        FIG_W, FIG_H = 11.69, 8.27

        # How much vertical space (in figure-fraction) to reserve for the paragraph above
        TOP_MARGIN    = 0.08   # blank top edge
        BOTTOM_MARGIN = 0.05   # blank bottom edge
        PARA_HEIGHT   = 0.10   # paragraph sits here — caller draws it separately,
                               # so we just leave this space empty at the top

        n_q = len(self.constants.answ_keys[:-1])

        # Divide remaining height equally among questions
        usable_height = 1.0 - TOP_MARGIN - BOTTOM_MARGIN - PARA_HEIGHT
        slot_h = usable_height / n_q          # total slot per question
        bar_frac  = 0.65                      # fraction of slot used by bar axes
        stat_frac = 0.20                      # fraction used by stats text axes

        LEFT   = 0.03
        WIDTH  = 0.94

        fig = plt.figure(figsize=(FIG_W, FIG_H))
        
        # Get precomputed statistics for this lecture
        # Use lecture_key (original name) if provided, otherwise try title
        stats_key = lecture_key if lecture_key is not None else title
        stats_dict = self.statistics.get(stats_key)

        for i, question in enumerate(self.constants.answ_keys[:-1]):
            # Slots are numbered top-to-bottom, so invert for matplotlib's
            # bottom-origin coordinate system
            slot_bottom = 1.0 - TOP_MARGIN - PARA_HEIGHT - (i + 1) * slot_h

            bar_bottom  = slot_bottom + (1.0 - bar_frac - stat_frac) * slot_h
            stat_bottom = slot_bottom + (1.0 - bar_frac - stat_frac * 1.4) * slot_h

            ax_bar  = fig.add_axes((LEFT, bar_bottom,  WIDTH, bar_frac  * slot_h))
            ax_stat = fig.add_axes((LEFT, stat_bottom, WIDTH, stat_frac * slot_h))

            # ── bar axes ──────────────────────────────────────────────────────
            ax_bar.invert_yaxis()
            ax_bar.axis("off")
            ax_bar.set_xlim(0, 100)

            labels      = self._labels_for_question(question)
            results_arr = results_dict[question]
            n           = len(results_arr)

            if n == 0:
                pct = np.zeros(len(self._labels_for_question(question)))
                pct_label = [""] * len(pct)
            else:
                # Use bincount to always produce a count for every Likert value (1–5),
                # even when some values are absent from the responses.
                # np.unique would silently drop missing values, causing bars to receive
                # wrong colors and labels (index-based k+1 ≠ actual Likert value).
                counts    = np.bincount(results_arr, minlength=6)[1:]  # indices 1–5
                pct       = np.round((counts / n) * 100, decimals=1)
                pct_label = [f"{k+1} ({pct[k]}%)" if pct[k] != 0 else ""
                             for k in range(5)]

            # start_pct für die linke Position jeder gestapelten Bar
            start_pct = np.concatenate([[0], np.cumsum(pct)[:-1]]) if len(pct) > 0 else np.array([])

            ax_bar.set_title(
                f"Question {i+1}: {self.constants.answer_titles[i]}",
                loc="left", pad=4, fontsize=9
            )
            rects = ax_bar.barh(
                np.full(len(pct), 0),
                width=pct,
                left=start_pct,
                height=0.5,
                color=self.constants.likert_palette,
                linewidth=0.02,
            )
            ax_bar.bar_label(rects, labels=pct_label, label_type="center", fontsize=8)
            ax_bar.legend(
                ncols=len(labels),
                handles=rects,
                labels=labels,
                bbox_to_anchor=(1.0, 1.08),
                loc="lower right",
                bbox_transform=ax_bar.transAxes,
                fontsize="small",
            )

            # ── stats axes ────────────────────────────────────────────────────
            if n > 5:
                # Use precomputed statistics from self.statistics for consistency
                # Look up stats by question name (not index) for correctness
                mean = None
                std = None
                
                if stats_dict is not None and question in stats_dict:
                    mean_stats, std_stats = stats_dict[question]
                    if mean_stats is not None:
                        mean = mean_stats
                        std = std_stats
                
                if mean is None:
                    mean = np.mean(results_arr)
                    std = np.std(results_arr, ddof=1)

                ax_stat.axis("off")
                ax_stat.text(
                    0.0, 0.1,
                    f"Mean and standard deviation: ${mean:.2f} \\pm {std:.2f}$",
                    transform=ax_stat.transAxes,
                    va="center", ha="left",
                    fontsize=8, color="black",
                )
            else:
                ax_stat.axis("off")
                ax_stat.text(
                    0.0, 0.1,
                    "Not enough votes for meaningful statistics.",
                    transform=ax_stat.transAxes,
                    va="center", ha="left",
                    fontsize=8, color="black",
                )


        img_buf = self._save_image_in_ram(fig)
        plt.close(fig)
        return img_buf

    def _write_pdf_with_graphs(self, title: str, total_count: int, img_buf: io.BytesIO, overall : bool = False, dna : int = 0) -> io.BytesIO:
        """
        Change: extracted PDF rendering for graphs into a helper to remove duplication.
        """
        pdf_graphs = FPDF(orientation="landscape")
        pdf_graphs.add_page()
        self._change_pdf_font(pdf_graphs)
        pdf_graphs.set_font("dejavu-sans", style="B", size=18)
        pdf_graphs.write(text=f"{title}\n\n")
        pdf_graphs.set_font("dejavu-sans", size=18)
        if overall:
            if dna == 0:
                pdf_graphs.write(text=f"A total of {total_count} questionnaires have been submitted.")
            else:
                pdf_graphs.write(text=f"A total of {total_count} questionnaires have been submitted. {dna} students did not attend the lecture(s).")
        else:
            pdf_graphs.write(text=f"A total of {total_count} questionnaires have been submitted.")
        image_y = pdf_graphs.get_y() + 6
        image_x = pdf_graphs.l_margin
        pdf_graphs.image(img_buf, x=image_x, y=image_y, w=pdf_graphs.w - 20)
        return io.BytesIO(pdf_graphs.output())

    def _create_results_pdf(self, lecture_dict: Dict, path:str) -> None:
        """
        Create PDFs for the given lecture dictionary (ML/AL/IL or overall).
        """
        if lecture_dict is self.overall_results:
            # overall survey results page
            img_buf = self._create_likert_figure(lecture_dict, "Overall Results", lecture_key="Overall Results")
            pdf_output = self._write_pdf_with_graphs("Overall Results", self.overall_count, img_buf)
            overall_pages = PdfReader(pdf_output).pages[0]

            # overall morning lectures results page
            img_buf = self._create_likert_figure(self.overall_morning, "Overall Morning Lecture Results", lecture_key="Overall Morning Lecture Results")
            total = len(self.overall_morning["interesting"])
            pdf_output = self._write_pdf_with_graphs("Overall Morning Lecture Results", total, img_buf, True, dna=self.dna_morning)
            morning_pages = PdfReader(pdf_output).pages[0]

            # overall afternoon lectures results page
            img_buf = self._create_likert_figure(self.overall_afternoon, "Overall Afternoon Lecture Results", lecture_key="Overall Afternoon Lecture Results")
            total = len(self.overall_afternoon["interesting"])
            pdf_output = self._write_pdf_with_graphs("Overall Afternoon Lecture Results", total, img_buf, True, dna=self.dna_afternoon)
            afternoon_pages = PdfReader(pdf_output).pages[0]

            # read in other necessary pages
            il_title_actual = list(self.il_title)[0]
            industry_pages = PdfReader(path + f"results_{il_title_actual.lower().replace(' ','_')}.pdf").pages[0]
            comment_pages = PdfReader(self._create_orga_topic_pdf()).pages

            # write everythin to one output pdf 
            writer = PdfWriter()
            writer.add_page(overall_pages)
            writer.add_page(morning_pages)
            writer.add_page(afternoon_pages)
            writer.add_page(industry_pages)
            for page in comment_pages:
                writer.add_page(page)
            output_path = path + "results_overall.pdf"
            writer.write(output_path)
        else:
            for lecture in lecture_dict.keys():
                title = f"Survey Results for {lecture}"
                total = len(lecture_dict[lecture]["interesting"])
                # Pass the original lecture name for statistics lookup, not the modified title
                img_buf = self._create_likert_figure(lecture_dict[lecture], title, lecture_key=lecture)
                if lecture_dict == self.il_results:
                    pdf_output = self._write_pdf_with_graphs(title, total, img_buf, True, self.dna_il)
                else:
                    pdf_output = self._write_pdf_with_graphs(title, total, img_buf)
                figure_page = PdfReader(pdf_output).pages[0]  
                comment_page = PdfReader(self._create_comment_pdf(lecture_dict[lecture]["comments"])).pages[0]
                writer = PdfWriter()
                writer.add_page(figure_page)
                writer.add_page(comment_page)
                output_path = path + f"results_{lecture.lower().replace(' ','_')}.pdf"
                writer.write(output_path)

    def _create_orga_topic_pdf(self) -> io.BytesIO:
        pdf_out = FPDF()
        self._change_pdf_font(pdf_out)   # <-- Fonts für dieses PDF registrieren
        
        # Get raw and clustered comments
        comments_orga_raw, comments_orga_clustered = self._comment_grouper(
            self.organization, use_semantic_split=False
        )
        comments_topics_raw, comments_topics_clustered = self._comment_grouper(
            self.topics, use_semantic_split=True
        )
        
        # Page 1: Clustered General Comments
        pdf_out.add_page()
        pdf_out.set_font("dejavu-sans", style="B", size=18)
        pdf_out.write(text="Clustered General Comments\n\n")
        pdf_out.set_font("dejavu-sans", size=10)
        pdf_out.write(text="The clustering has been performed using the \"all-MiniLM-L6-v2\" sentence transformer model available at https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2.\n\n")
        for txt in comments_orga_clustered:
            pdf_out.set_font("zapfdingbats", size=8)
            pdf_out.cell(w=5, h=5, text="l ")
            pdf_out.set_font("dejavu-sans", size=11)
            pdf_out.multi_cell(w=0, h=5, text=txt)
            pdf_out.ln()
        
        # Page 2: Clustered Topic Suggestions
        pdf_out.add_page()
        pdf_out.set_font("dejavu-sans", style="B", size=18)
        pdf_out.write(text="Clustered Topic Suggestions\n\n")
        pdf_out.set_font("dejavu-sans", size=10)
        pdf_out.write(text="The clustering has been performed using the \"all-MiniLM-L6-v2\" sentence transformer model available at https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2.\n\n")
        for txt in comments_topics_clustered:
            pdf_out.set_font("zapfdingbats", size=8)
            pdf_out.cell(w=5, h=5, text="l ")
            pdf_out.set_font("dejavu-sans", size=11)
            pdf_out.multi_cell(w=0, h=5, text=txt)
            pdf_out.ln()
        
        # Page 3: Original General Comments
        pdf_out.add_page()
        pdf_out.set_font("dejavu-sans", style="B", size=18)
        pdf_out.write(text="Original General Comments\n\n")
        for txt in comments_orga_raw:
            pdf_out.set_font("zapfdingbats", size=5)
            pdf_out.cell(w=5, h=2, text="l ")
            pdf_out.set_font("dejavu-sans", size=6)
            pdf_out.multi_cell(w=0, h=2, text=txt)
            pdf_out.ln()
        
        # Page 4: Original Topic Suggestions
        pdf_out.add_page()
        pdf_out.set_font("dejavu-sans", style="B", size=18)
        pdf_out.write(text="Original Topic Suggestions\n\n")
        for txt in comments_topics_raw:
            pdf_out.set_font("zapfdingbats", size=5)
            pdf_out.cell(w=5, h=2, text="l ")
            pdf_out.set_font("dejavu-sans", size=6)
            pdf_out.multi_cell(w=0, h=2, text=txt)
            pdf_out.ln()
        
        return io.BytesIO(pdf_out.output())

    def _perform_automated_analysis(self) -> None:
        self._fill_results_list()
        self._create_overall_results()
        self._create_overall_morning()
        self._create_overall_afternoon()
        
        # Calculate statistics for individual lectures
        self._calculate_lecture_statistics(self.ml_results)
        self._calculate_lecture_statistics(self.al_results)
        self._calculate_lecture_statistics(self.il_results)
        
        # Calculate statistics for overall results
        self._calculate_overall_statistics(self.overall_results, "Overall Results")
        self._calculate_overall_statistics(self.overall_morning, "Overall Morning Lecture Results")
        self._calculate_overall_statistics(self.overall_afternoon, "Overall Afternoon Lecture Results")

        if not os.path.exists(self.path_out):
            os.makedirs(self.path_out, exist_ok=True)

        self._create_results_pdf(self.ml_results, self.path_out)
        self._create_results_pdf(self.al_results, self.path_out)
        self._create_results_pdf(self.il_results, self.path_out)
        self._create_results_pdf(self.overall_results, self.path_out)

    # This method is based on Tom Aarsen's agglomerative.py sample code, retrieved at 10.02.2026: Source - https://github.com/huggingface/sentence-transformers/blob/main/examples/sentence_transformer/applications/clustering/agglomerative.py
    def _comment_grouper(self, corpus: List[str], use_semantic_split: bool = False,
                         split_similarity_threshold: float = 0.4):
        """
        Prepare *corpus* for agglomerative clustering and return both the raw and the
        clustered comment lists.

        Args:
            corpus: Raw comment strings (may contain None entries).
            use_semantic_split: When True, each comment is first split on commas to
                obtain candidate segments, then adjacent segments are re-merged when
                their cosine similarity is at or above *split_similarity_threshold*.
                This is appropriate for topic suggestions, where a comma can either
                separate two distinct topics or connect parts of the same thought.
                When False (default), each response is kept intact — appropriate for
                free-text organisation comments where commas are punctuation, not
                topic separators.
            split_similarity_threshold: Cosine-similarity threshold passed to
                _segment_by_semantic_similarity when use_semantic_split is True.
                Parts below this value are treated as distinct topics (default 0.4).
        """
        corpus_masked = [x for x in corpus if x is not None]
        corpus_split = []
        for comment in corpus_masked:
            if use_semantic_split:
                # Split on commas to get candidate segments, then let semantic
                # similarity decide which adjacent ones belong together.
                parts = [p.strip() for p in comment.split(",") if p.strip()]
                segments = self._segment_by_semantic_similarity(
                    parts, similarity_threshold=split_similarity_threshold
                )
                corpus_split.extend(segments)
            else:
                # Keep the full response intact; commas are punctuation here.
                stripped = comment.strip()
                if stripped:
                    corpus_split.append(stripped)
        corpus_embeddings = self.language_model.encode(corpus_split)
        clustering_model = AgglomerativeClustering(n_clusters=None, distance_threshold=0.4)
        clustering_model.fit(corpus_embeddings)
        cluster_assignment = clustering_model.labels_

        clustered_sentences: Dict[int, List[str]] = {}
        for sentence_id, cluster_id in enumerate(cluster_assignment):
            clustered_sentences.setdefault(cluster_id, []).append(corpus_split[sentence_id])

        clustered_answers = []
        grouped_answers = []
        for _, cluster in clustered_sentences.items():
            answ = f"{cluster[0]} (x{len(cluster)})"
            clustered_answers.append(answ)
            grouped_answers += cluster
        return grouped_answers, clustered_answers


if __name__ == "__main__":
    print("Starting script.")
    obj = SurveyAnalyzer()
    obj._perform_automated_analysis()
    print("Finished script.")