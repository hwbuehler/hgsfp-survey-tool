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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "all-MiniLM-L6-v2")
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
    def __init__(self, il_title: str = "IL1", data_path: str | None = None, output_path: str | None = None) -> None:
        # Change: allow passing an explicit data path to make the class easier to reuse/test.
        self.data, self.overall_count = self._read_data(data_path)
        self.path_out = output_path+'/' if output_path is not None else sys.argv[2] + '/'
        self.ml_titles, self.al_titles = self._determine_lecture_titles()
        self.il_title = il_title
        self.constants = SurveyConstants()
        self.ml_results, self.al_results, self.il_results = self._initialize_results_list()
        self.overall_results = self._create_lecture_dictionary()
        self.organization: List[str] = []
        self.topics: List[str] = []
        self.dna_morning = 0
        self.dna_afternoon = 0
        self.dna_il = 0
        # Dictionaries containing mean and standard deviation for each question and lecture timeslot
        self.statistics = {}
        self.language_model = SentenceTransformer(MODEL_PATH)

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

    def _determine_lecture_titles(self) -> Tuple[set[str], set[str]]:
        """
        Extract morning and afternoon lecture titles.
        """
        ml_titles_tmp = set()
        al_titles_tmp = set()
        for entry in self.data:
            ml_titles_tmp.add(entry["ml_title"])
            al_titles_tmp.add(entry["al_title"])
        return ml_titles_tmp, al_titles_tmp

    def _create_lecture_dictionary(self) -> Dict[str, List[int]]:
        """
        Create empty result dictionary for each lecture.
        """
        return {key: [] for key in self.constants.answ_keys}

    def _create_overall_results(self) -> None:
        # Change: avoid mutating keys and build the totals in a single pass.
        for question in self.constants.answ_keys[:-1]:
            combined: List[int] = []
            for ml_lecture, al_lecture in zip(self.ml_results.values(), self.al_results.values()):
                combined.extend(ml_lecture[question])
                combined.extend(al_lecture[question])
            combined.extend(self.il_results[question])
            self.overall_results[question] = combined
        self.overall_results.pop("comments", None)

    def _initialize_results_list(self) -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, List]]:
        """
        Initialize lecture result dictionaries.
        """
        ml_results_tmp = {elem: self._create_lecture_dictionary() for elem in self.ml_titles}
        al_results_tmp = {elem: self._create_lecture_dictionary() for elem in self.al_titles}
        il_results_tmp = self._create_lecture_dictionary()
        return ml_results_tmp, al_results_tmp, il_results_tmp

    def _fill_results_list(self) -> None:
        """
        Populate the result dictionaries from the raw survey data.
        """
        for elem in self.data:
            ml_title_tmp = elem["ml_title"]
            al_title_tmp = elem["al_title"]
            
            # Handle morning lecture
            if ml_title_tmp == "did not attend":
                self.dna_morning += 1
            else:
                for key in self.constants.answ_keys[:-1]:
                    self.ml_results[ml_title_tmp][key].append(elem[f"ml_{key}"])
                if "sugg_lectures" in elem:
                    self.ml_results[ml_title_tmp]["comments"].append(elem["sugg_lectures"]["ml_comment"])
            
            # Handle afternoon lecture
            if al_title_tmp == "did not attend":
                self.dna_afternoon += 1
            else:
                for key in self.constants.answ_keys[:-1]:
                    self.al_results[al_title_tmp][key].append(elem[f"al_{key}"])
                if "sugg_lectures" in elem:
                    self.al_results[al_title_tmp]["comments"].append(elem["sugg_lectures"]["al_comment"])
            
            # Handle intermediate lecture
            if elem["il_attended"]:
                for key in self.constants.answ_keys[:-1]:
                    self.il_results[key].append(elem[f"il_{key}"])
                if "sugg_lectures" in elem:
                    self.il_results["comments"].append(elem["sugg_lectures"]["il_comment"])
            else:
                self.dna_il += 1
            
            # Handle organization and topics suggestions
            if "sugg_organization" in elem:
                self.organization.append(elem["sugg_organization"])
            if "sugg_topics" in elem:
                self.topics.append(elem["sugg_topics"])

    # Adapted from author Sean Benoit, retrieved at 09/02/2026: Source - https://www.fpdf.org/en/script/script56.php
    def _create_comment_pdf(self, comments: List[str]) -> io.BytesIO:
        """
        Create a PDF page containing bullet list of comments.
        """
        pdf = FPDF(orientation="landscape")
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=18)
        pdf.write(text="Comments \n\n")
        for txt in comments:
            if txt is None:
                continue
            pdf.set_font("zapfdingbats", size=8)
            pdf.cell(w=5, h=5, text="l ")
            pdf.set_font("Helvetica", size=11)
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
            
        Returns:
            Dictionary with structure {lecture_title: [[means for Q1-Q6], [stds for Q1-Q6]]}
        """
        for lecture_title, questions_dict in results_dict.items():
            means = []
            stds = []
            for question in self.constants.answ_keys[:-1]:
                results_arr = questions_dict[question]
                n = len(results_arr)
                if n > 5:
                    means.append(float(np.mean(results_arr)))
                    stds.append(float(np.std(results_arr)))
                else:
                    means.append(None)
                    stds.append(None)
            self.statistics[lecture_title] = [means, stds]

    def _create_statistics_table_page(self, lecture_key: str) -> io.BytesIO:
        """Create a one-page PDF table of question means and standard deviations.

        The table has two rows:
        - Row 0: question numbers (1-6)
        - Row 1: mean ± std for the corresponding question

        Below the table we add a note about the Likert scale.
        """
        stats = self.statistics.get(lecture_key)

        pdf_stats = FPDF(orientation="landscape")
        pdf_stats.add_page()
        pdf_stats.set_font("Helvetica", style="B", size=18)
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
            if stats is None:
                for question in self.constants.answer_titles:
                    row = table.row()
                    row.cell(question, border=CellBordersLayout.NONE)
                    row.cell("N/A", border=CellBordersLayout.NONE)
            else:
                means, stds = stats
                for question, mean, std in zip(self.constants.answer_titles, means, stds):
                    row = table.row()
                    row.cell(question, border=CellBordersLayout.NONE)
                    if mean is None or std is None:
                        row.cell("N/A", border=CellBordersLayout.NONE)
                    else:
                        row.cell(f"{mean:.2f} ± {std:.2f}", border=CellBordersLayout.NONE)

        pdf_stats.ln(6)
        pdf_stats.set_font("Helvetica", size=10)
        pdf_stats.write(text="Likert rating scheme: 1 (most negative) to 5 (most positive).\n")

        return io.BytesIO(pdf_stats.output())
    
    def _create_likert_figure(self, results_dict: Dict[str, List[int]], title: str) -> io.BytesIO:
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

            _, answers = np.unique(results_arr, return_counts=True)
            pct        = np.round((answers / n) * 100, decimals=1)
            pct_label  = [f"{k+1} ({pct[k]}%)" for k in range(len(pct)) if pct[k] != 0]
            start_pct  = [pct[:j].sum() for j in range(len(pct))]

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
            if n>5:
                mean = np.mean(results_arr)
                std  = np.std(results_arr)

                ax_stat.axis("off")
                ax_stat.text(
                    0.0, 0.1,
                    f"Mean and standard deviation: ${mean:.1f} \\pm {std:.1f}$",
                    transform=ax_stat.transAxes,
                    va="center", ha="left",
                    fontsize=8, color="black",
                )
            else:
                ax_stat.axis("off")
                ax_stat.text(
                    0.0, 0.1,
                    f"Not enough votes for meaningful statistics.",
                    transform=ax_stat.transAxes,
                    va="center", ha="left",
                    fontsize=8, color="black",
                )


        img_buf = self._save_image_in_ram(fig)
        plt.close(fig)
        return img_buf

    def _write_pdf_with_graphs(self, title: str, total_count: int, img_buf: io.BytesIO, overall : bool = False) -> io.BytesIO:
        """
        Change: extracted PDF rendering for graphs into a helper to remove duplication.
        """
        pdf_graphs = FPDF(orientation="landscape")
        pdf_graphs.add_page()
        pdf_graphs.set_font("Helvetica", style="B", size=18)
        pdf_graphs.write(text=f"{title}\n\n")
        pdf_graphs.set_font("Helvetica", size=18)
        if overall:
            pdf_graphs.write(text=f"A total of {self.overall_count} questionnaires have been submitted.")
            pdf_graphs.write(text=f'The percentages for each question are calculated based on the sum of it\'s been answered, i.e. {total_count}.')
        else:
            pdf_graphs.write(text=f"A total of {total_count} questionnaires have been submitted.")
        image_y = pdf_graphs.get_y() + 6
        image_x = pdf_graphs.l_margin
        pdf_graphs.image(img_buf, x=image_x, y=image_y, w=pdf_graphs.w - 20)
        return io.BytesIO(pdf_graphs.output())

    def _create_results_pdf(self, lecture_dict: Dict,path:str) -> None:
        """
        Create PDFs for the given lecture dictionary (ML/AL/IL or overall).
        """
        if lecture_dict is self.il_results:
            title = f"Survey Results for {self.il_title}"
            total = len(lecture_dict["interesting"])
            img_buf = self._create_likert_figure(lecture_dict, title)
            pdf_output = self._write_pdf_with_graphs(title, total, img_buf)
            figure_page = PdfReader(pdf_output).pages[0]
            comment_page = PdfReader(self._create_comment_pdf(lecture_dict["comments"])).pages[0]
            writer = PdfWriter()
            writer.add_page(figure_page)
            writer.add_page(comment_page)
            output_path = path + f"results_{self.il_title.lower().replace(' ','_')}.pdf"
            writer.write(output_path)
        elif lecture_dict is self.overall_results:
            title = "Overall Survey Results"
            total = len(lecture_dict["interesting"])
            img_buf = self._create_likert_figure(lecture_dict, title)
            pdf_output = self._write_pdf_with_graphs(title, total, img_buf, True)
            output_path = path + "results_overall.pdf"
            # Change: write directly since there are no comments in overall results.
            with open(output_path, "wb") as f:
                f.write(pdf_output.getbuffer())
        else:
            for lecture in lecture_dict.keys():
                title = f"Survey Results for {lecture}"
                total = len(lecture_dict[lecture]["interesting"])
                img_buf = self._create_likert_figure(lecture_dict[lecture], title)
                pdf_output = self._write_pdf_with_graphs(title, total, img_buf)
                figure_page = PdfReader(pdf_output).pages[0]
                comment_page = PdfReader(self._create_comment_pdf(lecture_dict[lecture]["comments"])).pages[0]
                writer = PdfWriter()
                writer.add_page(figure_page)
                writer.add_page(comment_page)
                output_path = path + f"results_{lecture.lower().replace(' ','_')}.pdf"
                writer.write(output_path)

    def _create_orga_topic_pdf(self, path:str) -> None:
        pdf_out = FPDF()
        
        # Get raw and clustered comments
        comments_orga_raw, comments_orga_clustered = self._comment_grouper(self.organization)
        comments_topics_raw, comments_topics_clustered = self._comment_grouper(self.topics)
        
        # Page 1: Clustered General Comments
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="Clustered General Comments\n\n")
        for txt in comments_orga_clustered:
            pdf_out.set_font("zapfdingbats", size=8)
            pdf_out.cell(w=5, h=5, text="l ")
            pdf_out.set_font("Helvetica", size=11)
            pdf_out.multi_cell(w=0, h=5, text=txt)
            pdf_out.ln()
        
        # Page 2: Clustered Topic Suggestions
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="Clustered Topic Suggestions\n\n")
        for txt in comments_topics_clustered:
            pdf_out.set_font("zapfdingbats", size=8)
            pdf_out.cell(w=5, h=5, text="l ")
            pdf_out.set_font("Helvetica", size=11)
            pdf_out.multi_cell(w=0, h=5, text=txt)
            pdf_out.ln()
        
        # Page 3: Original General Comments
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="Original General Comments\n\n")
        for txt in comments_orga_raw:
            pdf_out.set_font("zapfdingbats", size=5)
            pdf_out.cell(w=5, h=2, text="l ")
            pdf_out.set_font("Helvetica", size=6)
            pdf_out.multi_cell(w=0, h=2, text=txt)
            pdf_out.ln()
        
        # Page 4: Original Topic Suggestions
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="Original Topic Suggestions\n\n")
        for txt in comments_topics_raw:
            pdf_out.set_font("zapfdingbats", size=5)
            pdf_out.cell(w=5, h=2, text="l ")
            pdf_out.set_font("Helvetica", size=6)
            pdf_out.multi_cell(w=0, h=2, text=txt)
            pdf_out.ln()
        
        output_path = self.path_out + "comments_topics.pdf"
        pdf_out.output(output_path)

    def _perform_automated_analysis(self) -> None:
        self._fill_results_list()
        self._create_overall_results()
        self._calculate_lecture_statistics(self.ml_results)
        self._calculate_lecture_statistics(self.al_results)
        self._calculate_lecture_statistics({self.il_title: self.il_results})
        if os.path.exists(self.path_out):
            self._create_results_pdf(self.ml_results, self.path_out)
            self._create_results_pdf(self.al_results, self.path_out)
            self._create_results_pdf(self.il_results, self.path_out)
            self._create_results_pdf(self.overall_results, self.path_out)
            self._create_orga_topic_pdf(self.path_out)
        else:
            os.makedirs(self.path_out)
            self._perform_automated_analysis()

    # This method is based on Tom Aarsen's agglomerative.py sample code, retrieved at 10.02.2026: Source - https://github.com/huggingface/sentence-transformers/blob/main/examples/sentence_transformer/applications/clustering/agglomerative.py
    def _comment_grouper(self, corpus: List[str]):
        corpus_masked = [x for x in corpus if x is not None]
        corpus_embeddings = self.language_model.encode(corpus_masked)
        clustering_model = AgglomerativeClustering(n_clusters=None, distance_threshold=0.4)
        clustering_model.fit(corpus_embeddings)
        cluster_assignment = clustering_model.labels_

        clustered_sentences: Dict[int, List[str]] = {}
        for sentence_id, cluster_id in enumerate(cluster_assignment):
            clustered_sentences.setdefault(cluster_id, []).append(corpus_masked[sentence_id])

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
