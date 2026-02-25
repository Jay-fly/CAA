BASE_URL = "https://dronegis.caa.gov.tw/server/rest/services/Hosted"

LAYERS = {
    "UAV": {
        "endpoint": "/UAV_fs/FeatureServer/3",
        "type": "uav",
        "name_field": "空域名稱",
    },
    "National_Park": {
        "endpoint": "/National_Park_fs/FeatureServer/0",
        "type": "national_park",
        "name_field": "name_full",
    },
    "Temporary_Area": {
        "endpoint": "/Temporary_Area/FeatureServer/19",
        "type": "temporary",
        "name_field": "空域名稱",
    },
    "Commercial_Port": {
        "endpoint": "/Commercial_Port_fs/FeatureServer/4",
        "type": "commercial_port",
        "name_field": "名稱",
    },
    "Kinmen_Matsu": {
        "endpoint": "/Kinmen_Matsu_Drone_Zone_fs/FeatureServer/0",
        "type": "kinmen_matsu",
        "name_field": None,
    },
}

PAGE_SIZE = 2000
