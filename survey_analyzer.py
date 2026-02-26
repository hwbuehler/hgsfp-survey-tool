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
    def __init__(self, il_title: str = "IL1", data_path: str | None = None, output_path: str | None = None, summarize: bool = False) -> None:
        # Change: allow passing an explicit data path to make the class easier to reuse/test.
        self.data, self.overall_count = self.ReadData(data_path)
        self.path_out = output_path+'/' if output_path is not None else sys.argv[2] + '/'
        self.ml_titles, self.al_titles = self.DetermineLectureTitles()
        self.il_title = il_title
        self.constants = SurveyConstants()
        self.ml_results, self.al_results, self.il_results = self.InitializeResultsList()
        self.overall_results = self.CreateLectureDictionary()
        self.organization: List[str] = []
        self.topics: List[str] = []
        self.summarize = summarize
        self.language_model = SentenceTransformer("all-MiniLM-L6-v2")

    def ReadData(self, data_path: str | None = None) -> Tuple[List[Dict],int]:
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

    def DetermineLectureTitles(self) -> Tuple[set[str], set[str]]:
        """
        Extract morning and afternoon lecture titles.
        """
        ml_titles_tmp = set()
        al_titles_tmp = set()
        for entry in self.data:
            ml_titles_tmp.add(entry["ml_title"])
            al_titles_tmp.add(entry["al_title"])
        return ml_titles_tmp, al_titles_tmp

    def CreateLectureDictionary(self) -> Dict[str, List[int]]:
        """
        Create empty result dictionary for each lecture.
        """
        return {key: [] for key in self.constants.answ_keys}

    def CreateOverallResults(self) -> None:
        # Change: avoid mutating keys and build the totals in a single pass.
        for question in self.constants.answ_keys[:-1]:
            combined: List[int] = []
            for ml_lecture, al_lecture in zip(self.ml_results.values(), self.al_results.values()):
                combined.extend(ml_lecture[question])
                combined.extend(al_lecture[question])
            combined.extend(self.il_results[question])
            self.overall_results[question] = combined
        self.overall_results.pop("comments", None)

    def InitializeResultsList(self) -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, List]]:
        """
        Initialize lecture result dictionaries.
        """
        ml_results_tmp = {elem: self.CreateLectureDictionary() for elem in self.ml_titles}
        al_results_tmp = {elem: self.CreateLectureDictionary() for elem in self.al_titles}
        il_results_tmp = self.CreateLectureDictionary()
        return ml_results_tmp, al_results_tmp, il_results_tmp

    def FillResultsList(self) -> None:
        """
        Populate the result dictionaries from the raw survey data.
        """
        for elem in self.data:
            ml_title_tmp = elem["ml_title"]
            al_title_tmp = elem["al_title"]
            for key in self.constants.answ_keys[:-1]:
                self.ml_results[ml_title_tmp][key].append(elem[f"ml_{key}"])
                self.al_results[al_title_tmp][key].append(elem[f"al_{key}"])
            if elem["il_attended"]:
                for key in self.constants.answ_keys[:-1]:
                    self.il_results[key].append(elem[f"il_{key}"])
            if "sugg_lectures" in elem:
                self.ml_results[ml_title_tmp]["comments"].append(elem["sugg_lectures"]["ml_comment"])
                self.al_results[al_title_tmp]["comments"].append(elem["sugg_lectures"]["al_comment"])
                self.il_results["comments"].append(elem["sugg_lectures"]["il_comment"])
            if "sugg_organization" in elem:
                self.organization.append(elem["sugg_organization"])
            if "sugg_topics" in elem:
                self.topics.append(elem["sugg_topics"])

    # Adapted from author Sean Benoit, retrieved at 09/02/2026: Source - https://www.fpdf.org/en/script/script56.php
    def CreateCommentPDF(self, comments: List[str]) -> io.BytesIO:
        """
        Create a PDF page containing bullet list of comments.
        """
        pdf = FPDF()
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
    def SaveImageInRAM(self, fig) -> io.BytesIO:
        """
        Save matplotlib figure to an in-memory PNG.
        """
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        buf.seek(0)
        return buf

    def _labels_for_question(self, question: str) -> Tuple[str, ...]:
        return self.constants.labels_level if question == "level" else self.constants.labels

    def _create_likert_figure(self, results_dict: Dict[str, List[int]], title: str) -> io.BytesIO:
        """
        Change: factored out repeated plotting logic into a single helper to reduce duplication.
        Returns an in-memory PNG of the figure.
        """
        fig, axes = plt.subplots(nrows=len(self.constants.answ_keys[:-1]), ncols=1, figsize=(11, 6))
        axes = axes.flatten()
        for i, question in enumerate(self.constants.answ_keys[:-1]):
            axes[i].invert_yaxis()
            axes[i].axis("off")
            axes[i].set_xlim(0, 100)
            labels = self._labels_for_question(question)
            results_arr = results_dict[question]
            n = len(results_arr)
            # Based on Ozgur Vatansever's post, retrieved at 04.06.2026: Source - https://stackoverflow.com/a/28663910
            _, answers = np.unique(results_arr, return_counts=True)
            pct = np.round((answers / n) * 100, decimals=1)
            pct_label = [f"{pct[k]}%" for k in range(len(pct)) if pct[k] != 0]
            start_pct = [pct[:j].sum() for j in range(len(pct))]
            axes[i].set_title(f"Question {i+1}: {self.constants.answer_titles[i]}", loc="left")
            rects = axes[i].barh(
                np.full(len(pct), 0),
                width=pct,
                left=start_pct,
                height=0.5,
                color=self.constants.likert_palette,
                linewidth=0.02,
            )
            axes[i].bar_label(rects, labels=pct_label, label_type="center")
            axes[i].legend(
                ncols=len(labels),
                handles=rects,
                labels=labels,
                bbox_to_anchor=(1.0, 1.08),
                loc="lower right",
                bbox_transform=axes[i].transAxes,
                fontsize="small",
            )
        plt.tight_layout()
        img_buf = self.SaveImageInRAM(fig)
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
            pdf_graphs.write(text=f'The percentages for each question are calculated based on how often it\'s been answered, i.e. {total_count}.')
        else:
            pdf_graphs.write(text=f"A total of {total_count} questionnaires have been submitted.")
        image_y = pdf_graphs.get_y() + 6
        image_x = pdf_graphs.l_margin
        pdf_graphs.image(img_buf, x=image_x, y=image_y, w=pdf_graphs.w - 20)
        return io.BytesIO(pdf_graphs.output())

    def CreateResultsPDF(self, lecture_dict: Dict,path:str) -> None:
        """
        Create PDFs for the given lecture dictionary (ML/AL/IL or overall).
        """
        if lecture_dict is self.il_results:
            title = f"Survey Results for {self.il_title}"
            total = len(lecture_dict["interesting"])
            img_buf = self._create_likert_figure(lecture_dict, title)
            pdf_output = self._write_pdf_with_graphs(title, total, img_buf)
            figure_page = PdfReader(pdf_output).pages[0]
            comment_page = PdfReader(self.CreateCommentPDF(lecture_dict["comments"])).pages[0]
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
                comment_page = PdfReader(self.CreateCommentPDF(lecture_dict[lecture]["comments"])).pages[0]
                writer = PdfWriter()
                writer.add_page(figure_page)
                writer.add_page(comment_page)
                output_path = path + f"results_{lecture.lower().replace(' ','_')}.pdf"
                writer.write(output_path)

    def CreateOrgaTopicPDF(self, path:str,clustering: bool = False) -> None:
        pdf_out = FPDF()
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="General Comments\n\n")
        if clustering:
            _, comments_orga = self.CommentGrouper(self.organization)
            _, comments_topics = self.CommentGrouper(self.topics)
        else:
            comments_orga, _ = self.CommentGrouper(self.organization)
            comments_topics, _ = self.CommentGrouper(self.topics)
        for txt in comments_orga:
            pdf_out.set_font("zapfdingbats", size=8 if clustering else 5)
            pdf_out.cell(w=5, h=5 if clustering else 2, text="l ")
            pdf_out.set_font("Helvetica", size=11 if clustering else 6)
            pdf_out.multi_cell(w=0, h=5 if clustering else 2, text=txt)
            pdf_out.ln()
        pdf_out.add_page()
        pdf_out.set_font("Helvetica", style="B", size=18)
        pdf_out.write(text="Topic Suggestions\n\n")
        for txt in comments_topics:
            pdf_out.set_font("zapfdingbats", size=8 if clustering else 5)
            pdf_out.cell(w=5, h=5 if clustering else 2, text="l ")
            pdf_out.set_font("Helvetica", size=11 if clustering else 6)
            pdf_out.multi_cell(w=0, h=5 if clustering else 2, text=txt)
            pdf_out.ln()
        output_path = self.path_out + ("clustered_comments_topics.pdf" if clustering else "raw_comments_topics.pdf")
        pdf_out.output(output_path)

    def PerformAutomatedAnalysis(self) -> None:
        self.FillResultsList()
        self.CreateOverallResults()
        if os.path.exists(self.path_out):
            self.CreateResultsPDF(self.ml_results, self.path_out)
            self.CreateResultsPDF(self.al_results, self.path_out)
            self.CreateResultsPDF(self.il_results, self.path_out)
            self.CreateResultsPDF(self.overall_results, self.path_out)
            self.CreateOrgaTopicPDF(self.path_out, False)
            if self.summarize:
                self.CreateOrgaTopicPDF(self.path_out, True)
        else:
            os.makedirs(self.path_out)
            self.PerformAutomatedAnalysis()

    # This method is based on Tom Aarsen's agglomerative.py sample code, retrieved at 10.02.2026: Source - https://github.com/huggingface/sentence-transformers/blob/main/examples/sentence_transformer/applications/clustering/agglomerative.py
    def CommentGrouper(self, corpus: List[str]):
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
    obj.PerformAutomatedAnalysis()
    print("Finished script.")
