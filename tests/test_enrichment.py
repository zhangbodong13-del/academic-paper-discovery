from academic_paper_discovery.enrichment import extract_innovation


def test_extracts_proposed_method_sentence_from_abstract() -> None:
    abstract = (
        "Autofocus is important in robotic microscopy. "
        "We propose a disparity-aware method that combines stereo cues "
        "and blur features for robust focus estimation. "
        "Experiments demonstrate improved accuracy."
    )

    assert extract_innovation(abstract) == (
        "摘要提取：We propose a disparity-aware method that combines "
        "stereo cues and blur features for robust focus estimation."
    )


def test_prefers_innovation_sentence_over_result_sentence() -> None:
    abstract = (
        "The method achieves high accuracy on three datasets. "
        "This work introduces a new cross-modal alignment module "
        "for surgical image analysis."
    )

    assert extract_innovation(abstract) == (
        "摘要提取：This work introduces a new cross-modal alignment "
        "module for surgical image analysis."
    )


def test_returns_unverified_when_abstract_is_missing() -> None:
    assert extract_innovation(None) == "未核验"
    assert extract_innovation("") == "未核验"


def test_returns_unverified_without_innovation_evidence() -> None:
    abstract = (
        "The dataset contains 5000 images. "
        "Experiments were conducted using standard evaluation metrics."
    )

    assert extract_innovation(abstract) == "未核验"


def test_extracts_chinese_innovation_sentence() -> None:
    abstract = (
        "机器人显微成像对对焦精度要求较高。"
        "本文提出一种融合双目视差与模糊特征的自动对焦方法。"
        "实验结果表明该方法具有较高精度。"
    )

    assert extract_innovation(abstract) == (
        "摘要提取：本文提出一种融合双目视差与模糊特征的自动对焦方法。"
    )