#!/usr/bin/env python3
import dataclasses
from typing import Dict, List, Tuple

from bunkai.algorithm.bunkai_sbd.annotator.basic_annotator import BasicRule
from bunkai.algorithm.bunkai_sbd.annotator.constant import LAYER_NAME_FIRST
from bunkai.algorithm.bunkai_sbd.annotator.emoji_annotator import \
    EmojiAnnotator
from bunkai.algorithm.bunkai_sbd.annotator.emotion_expression_annotator import \
    EmotionExpressionAnnotator
from bunkai.algorithm.bunkai_sbd.annotator.facemark_detector import \
    FaceMarkDetector
from bunkai.algorithm.bunkai_sbd.annotator.linebreak_annotator import \
    LinebreakAnnotator
from bunkai.algorithm.bunkai_sbd.annotator.morph_annotator import \
    MorphAnnotatorJanome
from bunkai.base.annotation import Annotations, SpanAnnotation, TokenResult
from bunkai.base.annotator import AnnotationFilter

DEFAULT_RULE_TARGET = (LAYER_NAME_FIRST,
                       BasicRule.__name__,
                       LinebreakAnnotator.__name__,
                       EmojiAnnotator.__name__, EmotionExpressionAnnotator.__name__,
                       FaceMarkDetector.__name__)


@dataclasses.dataclass
class RuleObject(object):
    size_n: int
    rule_target_morpheme: str
    rule_word_surface: List[str]
    is_valid: bool = True

    def is_rule_valid(self,
                      sb_candidate_morpheme: str,
                      current_target_index: int,
                      index2token_obj: Dict[int, TokenResult]
                      ):
        if self.rule_target_morpheme != '*' and self.rule_target_morpheme != sb_candidate_morpheme:
            return False

        range_check = current_target_index + self.size_n
        i_rule_morpheme: int = 0
        for __check in range(current_target_index, range_check):
            if self.rule_word_surface[i_rule_morpheme] != index2token_obj[__check].word_surface:
                return False
            i_rule_morpheme += 1
        return True


MORPHEMES_AFTER_CANDIDATE = [
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['て']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['の']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['と']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['って']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['という']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['に']),
    RuleObject(size_n=1, rule_target_morpheme='*', rule_word_surface=['など']),
    RuleObject(size_n=2, rule_target_morpheme='*', rule_word_surface=['くらい', 'の']),
    RuleObject(size_n=2, rule_target_morpheme='*', rule_word_surface=['くらい', 'です']),
    RuleObject(size_n=2, rule_target_morpheme='*', rule_word_surface=['くらい', 'でし']),
    RuleObject(size_n=2, rule_target_morpheme='*', rule_word_surface=['も', 'あり']),
    RuleObject(size_n=2, rule_target_morpheme='*', rule_word_surface=['ほど', 'でし']),
]


class IndirectQuoteExceptionAnnotator(AnnotationFilter):
    def __init__(self, rule_targets: Tuple[str, ...] = DEFAULT_RULE_TARGET):
        super().__init__(rule_name=self.__class__.__name__)
        self.rule_targets = rule_targets

    @staticmethod
    def is_exception_particle(original_text: str,
                              start_index: int,
                              end_index: int,
                              index2token_obj: Dict[int, TokenResult]) -> bool:
        """
        形態素解析の結果、基本分割文字列の後ろが助詞だった場合は 分割を行わない.

        ただし、助詞のすべてのケースで分割するわけではない。ルールを参照して、分割可否を決定する.

        例: 合宿免許? の若者さん達でしょうか / スタッフ? と話し込み.

        :return: True: not SB False: SB.
        """
        __next_end_index = end_index
        # __next_end_indexが最後の文字の場合
        if __next_end_index == len(original_text):
            return False
        # 特殊なルール end_indexの次の文字が改行記号である場合: 改行記号の後の形態素を判定基準にする。
        if original_text[__next_end_index] == '\n':
            while original_text[__next_end_index] == '\n' and __next_end_index + 1 < len(original_text):
                __next_end_index += 1

        if __next_end_index not in index2token_obj:
            return False
        else:
            if any([rule_object.is_rule_valid(sb_candidate_morpheme=original_text[start_index:end_index],
                                              current_target_index=__next_end_index,
                                              index2token_obj=index2token_obj)
                    for rule_object in MORPHEMES_AFTER_CANDIDATE]):
                return True
            else:
                return False

    def __generate(self, anns: List[SpanAnnotation]) -> Dict[int, TokenResult]:
        index2tokens = {}
        __start_index = 0
        __tokenizer_anns = [
            ann for ann in anns if ann.rule_name == MorphAnnotatorJanome.__name__]
        __processed = []
        for ann in __tokenizer_anns:
            t_obj = ann.args['token']  # type: ignore
            if t_obj in __processed:
                continue
            __length = len(t_obj.word_surface)
            for __i in range(__start_index, __start_index + __length):
                index2tokens[__i] = t_obj
            __start_index += __length
            __processed.append(t_obj)
        else:
            return index2tokens

    def annotate(self, original_text: str,
                 spans: Annotations) -> Annotations:
        index2token_obj = self.__generate(list(
            spans.get_annotation_layer(MorphAnnotatorJanome.__name__)))

        __return_span_ann = []
        for target_rule_name in self.rule_targets:
            if target_rule_name == LinebreakAnnotator.__name__ and target_rule_name not in spans.name2order:
                continue
            for __s in spans.get_annotation_layer(target_rule_name):
                if self.is_exception_particle(original_text,
                                              __s.start_index,
                                              __s.end_index,
                                              index2token_obj=index2token_obj):
                    continue
                else:
                    __return_span_ann.append(__s)

        spans.add_annotation_layer(self.rule_name, self.unify_span_annotations(__return_span_ann))
        return spans
