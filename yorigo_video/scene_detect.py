from scenedetect import open_video, ContentDetector, SceneManager, StatsManager, scene_manager

def find_scenes(video_path):
    video_stream = open_video(video_path)
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)

    scene_manager.add_detector(ContentDetector())

    scene_manager.detect_scenes(video=video_stream)
    scene_list = scene_manager.get_scene_list()
    # for i, scene in enumerate(scene_list):
    #     print(
    #         'Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
    #             i + 1,
    #             scene[0].get_timecode(), scene[0].get_frames(),
    #             scene[1].get_timecode(), scene[1].get_frames(),))

    return scene_list

def save_scene_frame(video_path, save_dir):
    scenes = find_scenes(video_path)
    # print(scenes)
    video_stream = open_video(video_path)
    scene_manager.save_images(scenes, video_stream, 1, output_dir = save_dir)

    scene_time_list = get_time_list(scenes)

    return scene_time_list

def get_time_list(scenes):
    scene_time_list = []

    for scene in scenes:
        scene_time_list.append((scene[0].get_timecode(), scene[1].get_timecode()))

    return scene_time_list