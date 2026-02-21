from app.fsm import CallFSM, Step


def test_fsm_happy_path() -> None:
    fsm = CallFSM(call_id="c1")
    assert fsm.consume("start") == Step.FIO
    assert fsm.consume("иван иванов") == Step.DEPARTMENT
    assert fsm.consume("ит") == Step.CABINET
    assert fsm.consume("101") == Step.PROBLEM
    assert fsm.consume("не работает принтер") == Step.EXTRA
    assert fsm.consume("без доп") == Step.CONFIRM
    assert fsm.consume("1") == Step.COMPLETE


def test_fsm_retries_to_incomplete() -> None:
    fsm = CallFSM(call_id="c2")
    fsm.consume("start")
    assert fsm.consume("") == Step.FIO
    assert fsm.consume("") == Step.INCOMPLETE


def test_fsm_confirm_rejects() -> None:
    fsm = CallFSM(call_id="c3")
    fsm.consume("start")
    fsm.consume("иван")
    fsm.consume("it")
    fsm.consume("100")
    fsm.consume("problem")
    fsm.consume("extra")
    assert fsm.consume("2") == Step.INCOMPLETE
