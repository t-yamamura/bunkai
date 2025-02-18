#!/usr/bin/env python3
import dataclasses
import typing

import emoji
import emojis

from bunkai.base.annotation import Annotations, SpanAnnotation
from bunkai.base.annotator import Annotator

EMOJI_UNICODE_ENGLISH = emoji.UNICODE_EMOJI['en']  # type: ignore


"""This module detects Emoji"""

# You could set any emoji-category that functions as an end-of-sentence
DEFAULT_TARGET_EMOJI_CATEGORY = ('Smileys & Emotion', 'Symbols')


@dataclasses.dataclass
class EmojiText(object):
    start_index: int
    end_index: int
    category: typing.List[typing.Optional[str]]

    def get_span(self) -> int:
        return self.end_index - self.start_index

    def check_emoji_category(self, category: typing.Iterable[str]) -> bool:
        """Be True if the given category-name exists else False."""
        if len(set(category) & set(self.category)) > 0:
            return True
        else:
            return False


class EmojiAnnotator(Annotator):
    def __init__(self, default_target_emoji_category: typing.Tuple[str, ...] = DEFAULT_TARGET_EMOJI_CATEGORY):
        super().__init__(rule_name=self.__class__.__name__)
        self.default_target_emoji_category = default_target_emoji_category

    @staticmethod
    def get_emoji_info(emoji_character: str) -> typing.Optional[str]:
        """Get emoji info. return a name of a category."""
        info = emojis.db.get_emoji_by_code(emoji_character)
        try:
            if info is None:
                info = emojis.db.get_emoji_by_code(f'{emoji_character}\ufe0f')
                return info.category
            else:
                return info.category
        except AttributeError:
            return None

    def __find_emoji(self, text: str) -> typing.List[EmojiText]:
        """:return: spans of emoji index. [[start-index, end-index]]."""
        __i: int = 0
        emoji_spans = []
        emoji_categories = []
        is_emoji_span: bool = False
        span_emoji_start: int = 0
        for __i in range(len(text)):
            __emoji: str = text[__i]
            if __emoji in EMOJI_UNICODE_ENGLISH:
                if is_emoji_span and __i + 1 <= len(text) and text[__i + 1] not in EMOJI_UNICODE_ENGLISH:
                    # 絵文字の範囲終了
                    is_emoji_span = False
                    emoji_categories.append(self.get_emoji_info(text[__i]))
                    emoji_spans.append(EmojiText(span_emoji_start, __i + 1, emoji_categories))
                    emoji_categories = []
                elif is_emoji_span is False and __i + 2 <= len(text) and text[__i + 1] not in EMOJI_UNICODE_ENGLISH:
                    # 絵文字が1文字で終了の場合
                    emoji_spans.append(EmojiText(__i - 1, __i + 1, [self.get_emoji_info(text[__i])]))
                elif is_emoji_span is False and __i + 1 == len(text):
                    # テキストの末尾が絵文字の場合
                    emoji_spans.append(EmojiText(__i - 1, __i + 1, [self.get_emoji_info(text[__i])]))
                elif is_emoji_span is False:
                    # 絵文字範囲のスタート
                    is_emoji_span = True
                    span_emoji_start = __i
                    emoji_categories.append(self.get_emoji_info(text[__i]))
                elif is_emoji_span is True:
                    # 絵文字範囲の途中
                    emoji_categories.append(self.get_emoji_info(text[__i]))
        return emoji_spans

    def annotate(self,
                 original_text: str,
                 spans: Annotations,
                 emoji_threshold: int = 1) -> Annotations:
        __emoji_spans = self.__find_emoji(original_text)
        target_emoji = [e_span for e_span in __emoji_spans if e_span.get_span() >= emoji_threshold]
        target_emoji = [e for e in target_emoji if e.check_emoji_category(self.default_target_emoji_category)]

        __return = [SpanAnnotation(rule_name=self.rule_name,
                                   start_index=emoji.start_index,
                                   end_index=emoji.end_index,
                                   split_string_type=EmojiAnnotator.__name__,
                                   split_string_value=original_text[emoji.start_index:emoji.end_index],
                                   args={'emoji': emoji})
                    for emoji in target_emoji]
        spans = self.add_forward_rule(__return, spans)
        return spans
