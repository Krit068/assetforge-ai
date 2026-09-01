def test_prompt_analysis_requests_targeted_clarification(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={"prompt": "宝箱", "locale": "zh-CN", "asset_type": "prop"},
    )

    assert response.status_code == 200
    analysis = response.json()["data"]
    assert analysis["ready_to_generate"] is False
    assert [question["id"] for question in analysis["clarifying_questions"]] == [
        "style",
        "material",
        "features",
    ]
    assert all(len(question["options"]) == 4 for question in analysis["clarifying_questions"])
    assert analysis["clarifying_questions"][0]["options"][0] == {
        "value": "低多边形风格",
        "label": "低多边形",
        "description": "轮廓清晰，适合移动端或俯视角游戏",
    }


def test_unknown_subject_is_resolved_before_directional_details(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={"prompt": "做一个东西", "locale": "zh-CN", "asset_type": "auto"},
    )

    assert response.status_code == 200
    questions = response.json()["data"]["clarifying_questions"]
    assert [question["id"] for question in questions] == ["subject"]
    assert [option["label"] for option in questions[0]["options"]] == [
        "人物 / 角色",
        "武器 / 装备",
        "道具 / 物件",
        "环境 / 建筑",
    ]


def test_prompt_analysis_accepts_specific_description(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={
            "prompt": "低多边形古代青铜宝箱，兽首锁扣，适合俯视角动作游戏",
            "locale": "zh-CN",
            "asset_type": "prop",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["ready_to_generate"] is True
    assert response.json()["data"]["clarifying_questions"] == []


def test_custom_style_answer_is_not_asked_again(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={
            "prompt": (
                "一个宝箱\n补充需求：\n"
                "希望采用什么美术风格？ 水墨剪纸融合风格\n"
                "主要材质和颜色是什么？ 竹编与深红漆面\n"
                "有哪些必须保留的外形或结构特征？ 云纹锁扣与圆角箱盖"
            ),
            "locale": "zh-CN",
            "asset_type": "prop",
        },
    )

    assert response.status_code == 200
    analysis = response.json()["data"]
    assert analysis["ready_to_generate"] is True
    assert analysis["clarifying_questions"] == []


def test_character_questions_do_not_ask_for_material(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={"prompt": "人物", "locale": "zh-CN", "asset_type": "auto"},
    )

    assert response.status_code == 200
    analysis = response.json()["data"]
    question_ids = [question["id"] for question in analysis["clarifying_questions"]]
    assert analysis["detected_asset_type"] == "character"
    assert question_ids == ["style", "appearance", "pose"]
    assert "material" not in question_ids


def test_reference_image_is_enough_to_enter_confirmation_flow(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={
            "prompt": "",
            "locale": "zh-CN",
            "asset_type": "character",
            "has_reference_image": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "ready_to_generate": True,
        "clarity_score": 100,
        "detected_asset_type": "character",
        "clarifying_questions": [],
        "detected_accessories": [],
        "concept_image_count": 1,
    }


def test_xianxia_character_uses_themed_choices_and_separate_sword_plan(client):
    response = client.post(
        "/api/v1/prompts/analyze",
        json={"prompt": "仙侠剑修少女", "locale": "zh-CN", "asset_type": "character"},
    )

    assert response.status_code == 200
    analysis = response.json()["data"]
    assert analysis["detected_accessories"] == ["长剑"]
    assert analysis["concept_image_count"] == 5
    appearance = next(
        question for question in analysis["clarifying_questions"] if question["id"] == "appearance"
    )
    assert appearance["options"][0]["label"] == "仙门剑修"
    assert all(option["label"] != "现代休闲" for option in appearance["options"])
