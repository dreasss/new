from dataclasses import dataclass, field
from enum import Enum


class Step(str, Enum):
    GREETING = "GREETING"
    FIO = "FIO"
    DEPARTMENT = "DEPARTMENT"
    CABINET = "CABINET"
    PROBLEM = "PROBLEM"
    EXTRA = "EXTRA"
    CONFIRM = "CONFIRM"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass
class CallFSM:
    call_id: str
    step: Step = Step.GREETING
    retries: dict[Step, int] = field(default_factory=dict)
    data: dict[str, str] = field(default_factory=dict)
    speaker_confirmed: bool = False

    def _inc_retry(self, step: Step) -> int:
        current = self.retries.get(step, 0) + 1
        self.retries[step] = current
        return current

    def consume(self, utterance: str | None) -> Step:
        text = (utterance or "").strip()

        if self.step == Step.GREETING:
            self.step = Step.FIO
            return self.step

        if self.step == Step.FIO:
            if not text:
                if self._inc_retry(Step.FIO) >= 2:
                    self.step = Step.INCOMPLETE
                return self.step
            self.data["fio"] = " ".join(w.capitalize() for w in text.split())
            self.step = Step.DEPARTMENT
            return self.step

        if self.step == Step.DEPARTMENT:
            if not text:
                if self._inc_retry(Step.DEPARTMENT) >= 2:
                    self.step = Step.INCOMPLETE
                return self.step
            self.data["department"] = text.lower().replace("отд", "отдел").strip()
            self.step = Step.CABINET
            return self.step

        if self.step == Step.CABINET:
            if not text:
                if self._inc_retry(Step.CABINET) >= 2:
                    self.step = Step.INCOMPLETE
                return self.step
            self.data["cabinet"] = text.replace("кабинет", "").strip()
            self.step = Step.PROBLEM
            return self.step

        if self.step == Step.PROBLEM:
            if not text:
                if self._inc_retry(Step.PROBLEM) >= 2:
                    self.step = Step.INCOMPLETE
                return self.step
            self.data["problem"] = text
            self.step = Step.EXTRA
            return self.step

        if self.step == Step.EXTRA:
            self.data["extra"] = text
            self.step = Step.CONFIRM
            return self.step

        if self.step == Step.CONFIRM:
            if text.lower() in {"1", "да", "подтверждаю", "yes"}:
                self.step = Step.COMPLETE
            else:
                self.step = Step.INCOMPLETE
            return self.step

        return self.step
