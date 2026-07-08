Parser：PDF / DOCX 转文本
# app/infrastructure/parsers/base.py

from abc import ABC, abstractmethod


class ParsedResumeText:
    def __init__(self, raw_text: str, page_count: int | None = None):
        self.raw_text = raw_text
        self.page_count = page_count


class ResumeParser(ABC):
    version = "base"

    @abstractmethod
    def parse(self, file_path: str) -> ParsedResumeText:
        pass
# app/infrastructure/parsers/pdf_parser.py

from pypdf import PdfReader
from app.infrastructure.parsers.base import ResumeParser, ParsedResumeText


class PdfResumeParser(ResumeParser):
    version = "pdf-parser-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        reader = PdfReader(file_path)

        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")

        return ParsedResumeText(
            raw_text="\n\n".join(texts),
            page_count=len(reader.pages),
        )
# app/infrastructure/parsers/docx_parser.py

from docx import Document
from app.infrastructure.parsers.base import ResumeParser, ParsedResumeText


class DocxResumeParser(ResumeParser):
    version = "docx-parser-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = Document(file_path)
        raw_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,
        )
4. Extractor：文本转 ResumeFact
# app/infrastructure/extractors/base.py

from abc import ABC, abstractmethod
from typing import List
from app.domain.resume.schemas import ResumeFact


class ResumeExtractor(ABC):
    version = "base"

    @abstractmethod
    async def extract_facts(self, raw_text: str) -> List[ResumeFact]:
        pass
# app/infrastructure/extractors/llm_resume_extractor.py

from typing import List
from app.infrastructure.extractors.base import ResumeExtractor
from app.domain.resume.schemas import ResumeFact, Evidence


class LLMResumeExtractor(ResumeExtractor):
    version = "llm-extractor-v1"

    async def extract_facts(self, raw_text: str) -> List[ResumeFact]:
        """
        这里后续可以接 OpenAI / Claude / DeepSeek / 本地模型。
        当前先放 mock，重点是结构。
        """

        facts = []

        if "Redis" in raw_text:
            facts.append(
                ResumeFact(
                    fact_type="skill",
                    key="Redis",
                    value={
                        "name": "Redis",
                        "category": "backend_cache",
                    },
                    evidence=Evidence(
                        source_text="简历中提到了 Redis 相关经验",
                        section="skills",
                        confidence=0.85,
                    ),
                )
            )

        if "Kafka" in raw_text:
            facts.append(
                ResumeFact(
                    fact_type="skill",
                    key="Kafka",
                    value={
                        "name": "Kafka",
                        "category": "message_queue",
                    },
                    evidence=Evidence(
                        source_text="简历中提到了 Kafka 相关经验",
                        section="skills",
                        confidence=0.85,
                    ),
                )
            )

        return facts
5. Classifier：Facts 转 CandidateProfile
# app/infrastructure/classifiers/base.py

from abc import ABC, abstractmethod
from typing import List
from app.domain.resume.schemas import ResumeFact, CandidateProfile


class ResumeClassifier(ABC):
    version = "base"

    @abstractmethod
    def build_profile(self, facts: List[ResumeFact]) -> CandidateProfile:
        pass
# app/infrastructure/classifiers/rule_classifier.py

from typing import List
from app.infrastructure.classifiers.base import ResumeClassifier
from app.domain.resume.schemas import ResumeFact, CandidateProfile, Skill


class RuleBasedResumeClassifier(ResumeClassifier):
    version = "rule-classifier-v1"

    def build_profile(self, facts: List[ResumeFact]) -> CandidateProfile:
        profile = CandidateProfile()

        for fact in facts:
            if fact.fact_type == "skill":
                profile.skills.append(
                    Skill(
                        name=fact.value.get("name"),
                        category=fact.value.get("category"),
                        evidence=fact.evidence.source_text,
                        confidence=fact.evidence.confidence,
                    )
                )

        skill_names = {s.name.lower() for s in profile.skills}

        if "redis" in skill_names or "kafka" in skill_names:
            profile.ability_tags.append("backend")

        if "kafka" in skill_names:
            profile.interview_clues.append("可以追问 Kafka 在项目中的使用场景、消费可靠性和消息堆积处理。")

        if "redis" in skill_names:
            profile.interview_clues.append("可以追问 Redis 缓存一致性、热点 Key、缓存击穿和分布式锁。")

        return profile
