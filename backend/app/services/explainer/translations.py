from typing import Dict, Any

TRANSLATIONS_HI: Dict[str, Any] = {
    "disclaimer": "एआई-जनित निर्णय सहायता; अंतिम निर्णय अधिकृत एआईसीटीई अधिकारियों के पास सुरक्षित है।",
    "headline_blocked": "आवेदन अवरुद्ध: महत्वपूर्ण विनियामक अनुपालन कमियां पाई गईं",
    "headline_review": "आवेदन पर ध्यान आवश्यक: अनुपालन संबंधी मुद्दों का समाधान करें",
    "headline_ready": "आवेदन तैयार: सभी अनिवार्य अनुपालन शर्तें पूरी हैं",
    "plain_summary_prefix": "आपके आवेदन {app_id} (संस्थान: {inst_name}) में स्वतः जांच के दौरान {count} मुख्य अनुपालन विसंगतियां पाई गई हैं।",
    "plain_summary_suffix": "अनुमोदन प्रक्रिया को आगे बढ़ाने के लिए कृपया नीचे दिए गए सुधारात्मक कदमों का पालन करें।",
    "what_officials_will_review": "अधिकृत एआईसीटीई अधिकारी नवीनीकृत वैधानिक प्रमाण पत्र, भूमि स्वामित्व विलेख और भवन सुरक्षा अनुमोदन का भौतिक या पोर्टल सत्यापन करेंगे।",
    "causes": {
        "MISSING_DOCUMENT": {
            "name": "अनिवार्य दस्तावेज़ अनुपलब्ध",
            "template": "आपका आवेदन आगे नहीं बढ़ सकता क्योंकि अनिवार्य दस्तावेज़ ({doc_name}) संलग्न नहीं है ({rule_ref})। कृपया वैध वैधानिक प्रमाणपत्र अपलोड करें।",
            "fix": "पोर्टल पर वैध और अधिकृत {doc_name} अपलोड करें।",
            "effort": "निम्न",
        },
        "EXPIRED_DOCUMENT": {
            "name": "समाप्त हो चुका दस्तावेज़",
            "template": "आपका आवेदन आगे नहीं बढ़ सकता क्योंकि {doc_name} की वैधता समाप्त हो चुकी है ({rule_ref})। कम से कम 30 दिनों के लिए वैध नवीनीकृत प्रमाणपत्र अपलोड करें।",
            "fix": "सक्षम प्राधिकारी से नवीनीकृत प्रमाणपत्र प्राप्त कर अपलोड करें।",
            "effort": "मध्यम",
        },
        "EXPIRING_SOON": {
            "name": "शीघ्र समाप्त होने वाला दस्तावेज़",
            "template": "{doc_name} की वैधता शीघ्र समाप्त होने वाली है ({rule_ref})। निर्बाध संचालन के लिए समय पर नवीनीकरण सुनिश्चित करें।",
            "fix": "समय सीमा से पहले प्रमाणपत्र नवीनीकरण की प्रक्रिया शुरू करें।",
            "effort": "निम्न",
        },
        "DATA_MISMATCH": {
            "name": "डेटा बेमेल",
            "template": "{doc_name} में प्रस्तुत विवरण और संस्थान प्रोफ़ाइल के बीच विसंगति पाई गई है ({rule_ref})।",
            "fix": "दस्तावेज़ में उल्लिखित डेटा और आवेदन प्रपत्र के विवरण का मिलान कर सुधार करें।",
            "effort": "निम्न",
        },
        "VERIFICATION_FAILED": {
            "name": "सत्यापन विफल",
            "template": "{doc_name} का बाहरी पोर्टल से स्वतः सत्यापन सफल नहीं हुआ ({rule_ref})। आधिकारिक समीक्षा आवश्यक है।",
            "fix": "संबंधित पोर्टल रिकॉर्ड की स्थिति जांचें और सहायक साक्ष्य प्रस्तुत करें।",
            "effort": "मध्यम",
        },
        "ANOMALY_FLAG": {
            "name": "सत्यापन आवश्यक",
            "template": "{doc_name} में विसंगति या दोहराव का संकेत मिला है ({rule_ref})। आधिकारिक सत्यापन आवश्यक है।",
            "fix": "सुनिश्चित करें कि मूल, अहस्तांतरित और प्रामाणिक दस्तावेज़ ही अपलोड किया गया है।",
            "effort": "उच्च",
        },
        "INFRASTRUCTURE_GAP": {
            "name": "बुनियादी ढांचा कमी",
            "template": "{doc_name} के अनुसार बुनियादी ढांचा क्षमता निर्धारित एआईसीटीई मानकों से कम है ({rule_ref})।",
            "fix": "स्वीकृत पाठ्यक्रम क्षमता के अनुसार आवश्यक भूमि/भवन क्षेत्र का समायोजन या विस्तार करें।",
            "effort": "उच्च",
        },
        "THRESHOLD_NOT_MET": {
            "name": "मानदंड सीमा अपूर्ण",
            "template": "विनियामक न्यूनतम मानदंड ({doc_name}) पूर्ण नहीं हुआ है ({rule_ref})।",
            "fix": "एआईसीटीई अनुमोदन प्रक्रिया पुस्तिका (APH) के दिशा-निर्देशों के अनुसार संशोधन करें।",
            "effort": "मध्यम",
        },
        "INCOMPLETE_FIELD": {
            "name": "अपूर्ण अनिवार्य फ़ील्ड",
            "template": "{doc_name} में आवश्यक अनिवार्य फ़ील्ड रिक्त या अपूर्ण है ({rule_ref})।",
            "fix": "अनुभाग में जाकर अपूर्ण फ़ील्ड को सही जानकारी के साथ भरें।",
            "effort": "निम्न",
        },
    },
    "effort_map": {
        "Low": "निम्न",
        "Medium": "मध्यम",
        "High": "उच्च",
    },
}

TRANSLATIONS_EN: Dict[str, Any] = {
    "disclaimer": "AI-generated decision support; final decisions rest with authorised AICTE officials.",
    "headline_blocked": "Application Blocked: Critical Statutory Deficiencies Detected",
    "headline_review": "Application Needs Attention: Remediation Required",
    "headline_ready": "Application Ready: All Mandatory Checks Satisfied",
    "plain_summary_prefix": "Automated scrutiny of application {app_id} for {inst_name} identified {count} core compliance issues.",
    "plain_summary_suffix": "Please follow the prioritized remediation steps below to ensure eligibility for AICTE approval.",
    "what_officials_will_review": "AICTE scrutiny officials will examine renewed statutory certificates, building safety approvals, and institutional data reconciliation records.",
    "effort_map": {
        "Low": "Low",
        "Medium": "Medium",
        "High": "High",
    },
}

