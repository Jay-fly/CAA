BASE_URL = "https://dronegis.caa.gov.tw/server/rest/services/Hosted"

LAYERS = {
    "UAV": {"endpoint": "/UAV_fs/FeatureServer/3", "type": "uav"},
    "National_Park": {"endpoint": "/National_Park_fs/FeatureServer/0", "type": "national_park"},
    "Temporary_Area": {"endpoint": "/Temporary_Area/FeatureServer/19", "type": "temporary"},
    "Commercial_Port": {"endpoint": "/Commercial_Port_fs/FeatureServer/4", "type": "commercial_port"},
    "Kinmen_Matsu": {"endpoint": "/Kinmen_Matsu_Drone_Zone_fs/FeatureServer/0", "type": "kinmen_matsu"},
}

PAGE_SIZE = 2000
