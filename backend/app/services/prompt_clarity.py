from app.schemas.prompts import ClarificationQuestion, PromptAnalysisResponse


SUBJECT_TERMS = {
    "宝箱", "箱子", "剑", "刀", "枪", "弓", "盾", "武器", "家具", "椅", "桌",
    "床", "灯", "植物", "树", "花", "岩石", "石头", "建筑", "墙", "门", "窗",
    "雕像", "道具", "crate", "chest", "sword", "knife", "spear", "bow", "shield",
    "weapon", "chair", "table", "bed", "lamp", "plant", "tree", "flower", "rock",
    "building", "wall", "door", "window", "statue", "prop",
}
CHARACTER_TERMS = {
    "人物", "人形", "角色", "女生", "男生", "女人", "男人", "女孩", "男孩",
    "少女", "少年", "战士", "骑士", "法师", "character", "humanoid", "girl",
    "boy", "woman", "man", "warrior", "knight", "mage",
}
STYLE_TERMS = {
    "低多边形", "低模", "卡通", "写实", "手绘", "像素", "风格化", "科幻", "奇幻",
    "美术风格", "艺术风格", "风格要求",
    "中世纪", "赛博朋克", "古代", "low poly", "low-poly", "stylized", "cartoon",
    "realistic", "hand-painted", "sci-fi", "fantasy", "medieval", "cyberpunk",
    "visual style", "art style", "style requirement",
}
MATERIAL_TERMS = {
    "木", "石", "金属", "铁", "钢", "铜", "青铜", "银", "金", "玻璃", "陶瓷",
    "布", "皮革", "塑料", "水晶", "wood", "stone", "metal", "iron", "steel",
    "bronze", "copper", "silver", "gold", "glass", "ceramic", "cloth", "leather",
    "plastic", "crystal", "主要材质", "材质和颜色", "main material", "materials and colors",
}
FEATURE_TERMS = {
    "锁扣", "边角", "箱盖", "轮廓", "可动", "开合", "磨损", "破损", "裂纹",
    "缺口", "对称", "结构", "hinge", "clasp", "silhouette", "movable", "opening",
    "worn", "damaged", "crack", "chip", "symmetrical", "structure",
    "结构特征", "外形特征", "structural details", "shape details",
}
APPEARANCE_TERMS = {
    "外观", "服装", "长发", "短发", "连衣裙", "护甲", "披风", "长袍", "战斗服",
    "体型", "发色", "发型", "outfit", "appearance", "hair", "dress", "armor",
    "cape", "robe", "combat suit", "build",
}
POSE_TERMS = {
    "姿态", "姿势", "站姿", "a-pose", "t-pose", "自然站立", "动态展示",
    "pose", "standing", "neutral stance", "dynamic stance",
}

XIANXIA_TERMS = {
    "仙侠", "修仙", "古风", "仙门", "宗门", "剑修", "仙子", "道袍", "古装",
    "xianxia", "cultivator", "ancient chinese", "wuxia",
}

ACCESSORY_TERMS = (
    (("长剑", "佩剑", "宝剑", "剑", "sword"), "长剑", "sword"),
    (("盾牌", "盾", "shield"), "盾牌", "shield"),
    (("长弓", "弓箭", "弓", "bow"), "弓", "bow"),
    (("法杖", "魔杖", "staff", "wand"), "法杖", "staff"),
    (("长枪", "战枪", "spear", "lance"), "长枪", "spear"),
    (("双刀", "匕首", "dagger"), "匕首", "dagger"),
)

XIANXIA_APPEARANCE_OPTIONS = {
    "zh-CN": [
        ("仙门剑修外观", "仙门剑修", "古风道袍、束发与利落的修行者轮廓"),
        ("宗门弟子外观", "宗门弟子", "统一门派服饰、腰封与轻量护具"),
        ("云游散修外观", "云游散修", "层叠布衣、披肩与旅途使用痕迹"),
        ("华贵仙子外观", "华贵仙子", "飘逸古装、精致发饰与轻盈轮廓"),
    ],
    "en": [
        ("xianxia sword cultivator", "Sword cultivator", "Layered robes, tied hair, and a clean martial silhouette"),
        ("sect disciple appearance", "Sect disciple", "Coordinated sect robes, a sash, and light protection"),
        ("wandering cultivator", "Wandering cultivator", "Layered travel clothes, a shawl, and subtle wear"),
        ("elegant xianxia immortal", "Elegant immortal", "Flowing ancient attire, refined hair ornaments, and a light silhouette"),
    ],
}


def detect_accessories(prompt: str, locale: str = "zh-CN") -> list[str]:
    lowered = prompt.casefold()
    result: list[str] = []
    for aliases, zh_name, en_name in ACCESSORY_TERMS:
        if any(alias.casefold() in lowered for alias in aliases):
            result.append(en_name if locale == "en" else zh_name)
    return result[:3]


COPY = {
    "zh-CN": {
        "subject": ("你具体想生成什么物体？", "例如：宝箱、长剑、路灯或模块化石墙"),
        "style": ("希望采用什么美术风格？", "例如：低多边形、手绘卡通、写实或科幻"),
        "material": ("主要材质和颜色是什么？", "例如：深色橡木、氧化青铜、灰白石材"),
        "features": ("有哪些必须保留的外形或结构特征？", "例如：兽首锁扣、断裂边角、可开启箱盖"),
        "appearance": ("请补充人物的外观与服装特征。", "例如：成年女性、修长体型、白色连衣裙、黑色长发"),
        "pose": ("希望人物使用什么姿态？", "例如：A-pose 站立、自然站姿或保留参考图姿势"),
    },
    "en": {
        "subject": ("What object should be generated?", "For example: a chest, sword, street lamp, or modular stone wall"),
        "style": ("What visual style should it use?", "For example: low-poly, hand-painted cartoon, realistic, or sci-fi"),
        "material": ("What are its main materials and colors?", "For example: dark oak, oxidized bronze, or pale stone"),
        "features": ("Which shape or structural details must be preserved?", "For example: a beast-head clasp, chipped corners, or an opening lid"),
        "appearance": ("Describe the character's appearance and outfit.", "For example: adult woman, slender build, white dress, and long black hair"),
        "pose": ("What pose should the character use?", "For example: A-pose, neutral standing pose, or the reference pose"),
    },
}


OPTIONS = {
    "zh-CN": {
        "subject": [
            ("游戏角色", "人物 / 角色", "生成一个完整人物或人形角色"),
            ("武器装备", "武器 / 装备", "例如长剑、盾牌、枪械或护甲"),
            ("场景道具", "道具 / 物件", "例如宝箱、家具、机关或装饰物"),
            ("环境建筑", "环境 / 建筑", "例如房屋、门墙、遗迹或模块化场景件"),
        ],
        "style": [
            ("低多边形风格", "低多边形", "轮廓清晰，适合移动端或俯视角游戏"),
            ("手绘卡通风格", "手绘卡通", "色块明确，带手绘纹理质感"),
            ("写实 PBR 风格", "写实 PBR", "真实材质、光照与表面细节"),
            ("科幻硬表面风格", "科幻硬表面", "机械结构、硬边和科技细节"),
        ],
        "material": [
            ("木材与金属包边", "木材 + 金属", "木质主体，使用金属连接与包边"),
            ("氧化青铜材质", "氧化青铜", "青铜主体，带自然氧化与旧化痕迹"),
            ("灰白石材", "石材", "粗糙石质表面，适合建筑或遗迹"),
            ("水晶与玻璃材质", "水晶 / 玻璃", "半透明或高光材质表现"),
        ],
        "features": [
            ("强化游戏识别轮廓", "轮廓优先", "保持远距离和俯视角下易于识别"),
            ("包含可开合或可动结构", "可动结构", "保留箱盖、门轴、关节等可动部分"),
            ("加入磨损和破损细节", "磨损 / 破损", "增加使用痕迹、裂纹或缺口"),
            ("保持整洁对称外形", "整洁对称", "减少噪声细节，突出规整结构"),
        ],
        "appearance": [
            ("奇幻战士外观", "奇幻战士", "护甲、披风与清晰的战斗轮廓"),
            ("奇幻法师外观", "奇幻法师", "长袍、法术配饰与轻盈轮廓"),
            ("现代休闲外观", "现代休闲", "日常服装与自然人物比例"),
            ("科幻战斗服外观", "科幻战斗服", "贴身装甲、机械组件与科技细节"),
        ],
        "pose": [
            ("A-pose 标准站姿", "A-pose", "手臂略微展开，便于后续绑定骨骼"),
            ("T-pose 标准站姿", "T-pose", "手臂水平展开，适合传统绑定流程"),
            ("自然中立站姿", "自然站姿", "双臂自然下垂，强调展示效果"),
            ("轻微动态展示姿势", "动态展示", "保留稳定重心并增加角色表现力"),
        ],
    },
    "en": {
        "subject": [
            ("game character", "Character", "A complete human or humanoid game character"),
            ("weapon or equipment", "Weapon / gear", "A sword, shield, firearm, armor, or similar item"),
            ("environment prop", "Prop / object", "A chest, furniture item, mechanism, or decoration"),
            ("environment building", "Environment / building", "A structure, ruin, wall, door, or modular scene piece"),
        ],
        "style": [
            ("low-poly style", "Low-poly", "A readable silhouette suited to mobile or top-down games"),
            ("hand-painted cartoon style", "Hand-painted", "Clear color blocks with a painted texture treatment"),
            ("realistic PBR style", "Realistic PBR", "Physically based materials and realistic surface detail"),
            ("sci-fi hard-surface style", "Sci-fi hard surface", "Mechanical forms, hard edges, and technical details"),
        ],
        "material": [
            ("wood with metal trim", "Wood + metal", "A wooden body with metal joints and protective trim"),
            ("oxidized bronze", "Oxidized bronze", "Bronze surfaces with natural patina and wear"),
            ("pale gray stone", "Stone", "A rough stone surface suited to architecture or ruins"),
            ("crystal and glass", "Crystal / glass", "Translucent or glossy material treatment"),
        ],
        "features": [
            ("game-readable silhouette", "Silhouette first", "Keep the asset recognizable at distance and from above"),
            ("movable or opening parts", "Movable parts", "Preserve lids, hinges, joints, or other moving structures"),
            ("worn and damaged details", "Wear / damage", "Add scratches, cracks, chips, or signs of use"),
            ("clean symmetrical shape", "Clean symmetry", "Reduce noise and emphasize an orderly structure"),
        ],
        "appearance": [
            ("fantasy warrior appearance", "Fantasy warrior", "Armor, a cape, and a strong combat silhouette"),
            ("fantasy mage appearance", "Fantasy mage", "Robes, magical accessories, and a lighter silhouette"),
            ("modern casual appearance", "Modern casual", "Everyday clothing and natural proportions"),
            ("sci-fi combat suit", "Sci-fi combat suit", "Fitted armor, mechanical parts, and technical details"),
        ],
        "pose": [
            ("standard A-pose", "A-pose", "Arms slightly lowered for convenient rigging"),
            ("standard T-pose", "T-pose", "Arms held horizontally for a traditional rigging workflow"),
            ("neutral standing pose", "Neutral standing", "Arms relaxed to emphasize presentation"),
            ("subtle dynamic showcase pose", "Dynamic showcase", "A stable stance with more character expression"),
        ],
    },
}


def _contains_any(prompt: str, terms: set[str]) -> bool:
    lowered = prompt.casefold()
    return any(term.casefold() in lowered for term in terms)


def analyze_prompt(
    prompt: str,
    locale: str = "zh-CN",
    asset_type: str = "auto",
    has_reference_image: bool = False,
) -> PromptAnalysisResponse:
    cleaned = " ".join(prompt.strip().split())
    detected_asset_type = (
        "character"
        if asset_type == "character" or (asset_type == "auto" and _contains_any(cleaned, CHARACTER_TERMS))
        else "prop"
    )
    accessories = detect_accessories(cleaned, locale) if detected_asset_type == "character" else []
    concept_image_count = (4 + len(accessories)) if detected_asset_type == "character" else 1
    if has_reference_image:
        return PromptAnalysisResponse(
            ready_to_generate=True,
            clarity_score=100,
            detected_asset_type=detected_asset_type,
            clarifying_questions=[],
            detected_accessories=accessories,
            concept_image_count=1,
        )

    has_subject = _contains_any(cleaned, SUBJECT_TERMS | CHARACTER_TERMS)
    has_style = _contains_any(cleaned, STYLE_TERMS)
    has_material = _contains_any(cleaned, MATERIAL_TERMS)
    has_features = _contains_any(cleaned, FEATURE_TERMS)
    has_appearance = _contains_any(cleaned, APPEARANCE_TERMS)
    has_pose = _contains_any(cleaned, POSE_TERMS)

    missing: list[str] = []
    if not has_subject:
        # Resolve the subject first so the next turn can ask character-specific
        # or prop-specific details without showing irrelevant choices.
        missing.append("subject")
    else:
        if not has_style:
            missing.append("style")
        if detected_asset_type == "character":
            if not has_appearance:
                missing.append("appearance")
            if not has_pose:
                missing.append("pose")
        else:
            if not has_material:
                missing.append("material")
            if not has_features:
                missing.append("features")

    missing = missing[:3]
    active_locale = locale if locale in COPY else "zh-CN"
    localized = COPY[active_locale]
    localized_options = OPTIONS[active_locale]
    xianxia = _contains_any(cleaned, XIANXIA_TERMS)
    questions = [
        ClarificationQuestion(
            id=question_id,
            question=localized[question_id][0],
            answer_hint=localized[question_id][1],
            options=[
                {"value": value, "label": label, "description": description}
                for value, label, description in (
                    XIANXIA_APPEARANCE_OPTIONS[active_locale]
                    if question_id == "appearance" and xianxia
                    else localized_options[question_id]
                )
            ],
        )
        for question_id in missing
    ]
    return PromptAnalysisResponse(
        ready_to_generate=not questions,
        clarity_score=max(0, 100 - len(missing) * 30),
        detected_asset_type=detected_asset_type,
        clarifying_questions=questions,
        detected_accessories=accessories,
        concept_image_count=concept_image_count,
    )
