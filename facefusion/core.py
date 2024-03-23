import os

os.environ['OMP_NUM_THREADS'] = '1'

import shutil
import signal
import sys
import time
import warnings
import shutil
import numpy
import onnxruntime
import multiprocessing
from time import sleep
from argparse import ArgumentParser, HelpFormatter
from const_define import *

import facefusion.choices
import facefusion.globals
from facefusion.face_analyser import get_one_face, get_average_face
from facefusion.face_store import get_reference_faces, append_reference_face, clear_static_faces, clear_reference_faces
from facefusion import face_analyser, face_masker, content_analyser, config, metadata, logger, wording
from facefusion.content_analyser import analyse_image, analyse_video
from facefusion.processors.frame.core import get_frame_processors_modules, load_frame_processor_module
from facefusion.common_helper import create_metavar, get_first
from facefusion.execution_helper import encode_execution_providers, decode_execution_providers
from facefusion.normalizer import normalize_output_path, normalize_padding, normalize_fps
from facefusion.memory import limit_system_memory
from facefusion.filesystem import list_directory, get_temp_frame_paths, create_temp, move_temp, clear_temp, is_image, is_video, filter_audio_paths
from facefusion.ffmpeg import extract_frames, compress_image, merge_video, restore_audio, replace_audio
from facefusion.vision import get_video_frame, read_image, read_static_images, pack_resolution, detect_video_resolution, detect_video_fps, create_video_resolutions

onnxruntime.set_default_logger_severity(3)
warnings.filterwarnings('ignore', category = UserWarning, module = 'gradio')
warnings.filterwarnings('ignore', category = UserWarning, module = 'torchvision')


def cli() -> None:
    signal.signal(signal.SIGINT, lambda signal_number, frame: destroy())
    program = ArgumentParser(formatter_class = lambda prog: HelpFormatter(prog, max_help_position = 130), add_help = False)
    # general
    program.add_argument('-s', '--source', help = wording.get('help.source'), action = 'append', dest = 'source_paths', default = config.get_str_list('general.source_paths'))
    program.add_argument('-t', '--target', help = wording.get('help.target'), dest = 'target_path', default = config.get_str_value('general.target_path'))
    program.add_argument('-o', '--output', help = wording.get('help.output'), dest = 'output_path', default = config.get_str_value('general.output_path'))
    program.add_argument('-v', '--version', version = metadata.get('name') + ' ' + metadata.get('version'), action = 'version')
    # misc
    group_misc = program.add_argument_group('misc')
    group_misc.add_argument('--skip-download', help = wording.get('help.skip_download'), action = 'store_true', default = config.get_bool_value('misc.skip_download'))
    group_misc.add_argument('--headless', help = wording.get('help.headless'), action = 'store_true', default = config.get_bool_value('misc.headless'))
    group_misc.add_argument('--log-level', help = wording.get('help.log_level'), default = config.get_str_value('misc.log_level', 'info'), choices = logger.get_log_levels())
    # execution
    execution_providers = encode_execution_providers(onnxruntime.get_available_providers())
    group_execution = program.add_argument_group('execution')
    group_execution.add_argument('--execution-providers', help = wording.get('help.execution_providers').format(choices = ', '.join(execution_providers)), default = config.get_str_list('execution.execution_providers', 'cpu'), choices = execution_providers, nargs = '+', metavar = 'EXECUTION_PROVIDERS')
    group_execution.add_argument('--execution-thread-count', help = wording.get('help.execution_thread_count'), type = int, default = config.get_int_value('execution.execution_thread_count', '4'), choices = facefusion.choices.execution_thread_count_range, metavar = create_metavar(facefusion.choices.execution_thread_count_range))
    group_execution.add_argument('--execution-queue-count', help = wording.get('help.execution_queue_count'), type = int, default = config.get_int_value('execution.execution_queue_count', '1'), choices = facefusion.choices.execution_queue_count_range, metavar = create_metavar(facefusion.choices.execution_queue_count_range))
    # memory
    group_memory = program.add_argument_group('memory')
    group_memory.add_argument('--video-memory-strategy', help = wording.get('help.video_memory_strategy'), default = config.get_str_value('memory.video_memory_strategy', 'strict'), choices = facefusion.choices.video_memory_strategies)
    group_memory.add_argument('--system-memory-limit', help = wording.get('help.system_memory_limit'), type = int, default = config.get_int_value('memory.system_memory_limit', '0'), choices = facefusion.choices.system_memory_limit_range, metavar = create_metavar(facefusion.choices.system_memory_limit_range))
    # face analyser
    group_face_analyser = program.add_argument_group('face analyser')
    group_face_analyser.add_argument('--face-analyser-order', help = wording.get('help.face_analyser_order'), default = config.get_str_value('face_analyser.face_analyser_order', 'left-right'), choices = facefusion.choices.face_analyser_orders)
    group_face_analyser.add_argument('--face-analyser-age', help = wording.get('help.face_analyser_age'), default = config.get_str_value('face_analyser.face_analyser_age'), choices = facefusion.choices.face_analyser_ages)
    group_face_analyser.add_argument('--face-analyser-gender', help = wording.get('help.face_analyser_gender'), default = config.get_str_value('face_analyser.face_analyser_gender'), choices = facefusion.choices.face_analyser_genders)
    group_face_analyser.add_argument('--face-detector-model', help = wording.get('help.face_detector_model'), default = config.get_str_value('face_analyser.face_detector_model', 'yoloface'), choices = facefusion.choices.face_detector_set.keys())
    group_face_analyser.add_argument('--face-detector-size', help = wording.get('help.face_detector_size'), default = config.get_str_value('face_analyser.face_detector_size', '640x640'))
    group_face_analyser.add_argument('--face-detector-score', help = wording.get('help.face_detector_score'), type = float, default = config.get_float_value('face_analyser.face_detector_score', '0.5'), choices = facefusion.choices.face_detector_score_range, metavar = create_metavar(facefusion.choices.face_detector_score_range))
    # face selector
    group_face_selector = program.add_argument_group('face selector')
    group_face_selector.add_argument('--face-selector-mode', help = wording.get('help.face_selector_mode'), default = config.get_str_value('face_selector.face_selector_mode', 'reference'), choices = facefusion.choices.face_selector_modes)
    group_face_selector.add_argument('--reference-face-position', help = wording.get('help.reference_face_position'), type = int, default = config.get_int_value('face_selector.reference_face_position', '0'))
    group_face_selector.add_argument('--reference-face-distance', help = wording.get('help.reference_face_distance'), type = float, default = config.get_float_value('face_selector.reference_face_distance', '0.6'), choices = facefusion.choices.reference_face_distance_range, metavar = create_metavar(facefusion.choices.reference_face_distance_range))
    group_face_selector.add_argument('--reference-frame-number', help = wording.get('help.reference_frame_number'), type = int, default = config.get_int_value('face_selector.reference_frame_number', '0'))
    # face mask
    group_face_mask = program.add_argument_group('face mask')
    group_face_mask.add_argument('--face-mask-types', help = wording.get('help.face_mask_types').format(choices = ', '.join(facefusion.choices.face_mask_types)), default = config.get_str_list('face_mask.face_mask_types', 'box'), choices = facefusion.choices.face_mask_types, nargs = '+', metavar = 'FACE_MASK_TYPES')
    group_face_mask.add_argument('--face-mask-blur', help = wording.get('help.face_mask_blur'), type = float, default = config.get_float_value('face_mask.face_mask_blur', '0.3'), choices = facefusion.choices.face_mask_blur_range, metavar = create_metavar(facefusion.choices.face_mask_blur_range))
    group_face_mask.add_argument('--face-mask-padding', help = wording.get('help.face_mask_padding'), type = int, default = config.get_int_list('face_mask.face_mask_padding', '0 0 0 0'), nargs = '+')
    group_face_mask.add_argument('--face-mask-regions', help = wording.get('help.face_mask_regions').format(choices = ', '.join(facefusion.choices.face_mask_regions)), default = config.get_str_list('face_mask.face_mask_regions', ' '.join(facefusion.choices.face_mask_regions)), choices = facefusion.choices.face_mask_regions, nargs = '+', metavar = 'FACE_MASK_REGIONS')
    # frame extraction
    group_frame_extraction = program.add_argument_group('frame extraction')
    group_frame_extraction.add_argument('--trim-frame-start', help = wording.get('help.trim_frame_start'), type = int, default = facefusion.config.get_int_value('frame_extraction.trim_frame_start'))
    group_frame_extraction.add_argument('--trim-frame-end',    help = wording.get('help.trim_frame_end'), type = int, default = facefusion.config.get_int_value('frame_extraction.trim_frame_end'))
    group_frame_extraction.add_argument('--temp-frame-format', help = wording.get('help.temp_frame_format'), default = config.get_str_value('frame_extraction.temp_frame_format', 'jpg'), choices = facefusion.choices.temp_frame_formats)
    group_frame_extraction.add_argument('--temp-frame-quality', help = wording.get('help.temp_frame_quality'), type = int, default = config.get_int_value('frame_extraction.temp_frame_quality', '100'), choices = facefusion.choices.temp_frame_quality_range, metavar = create_metavar(facefusion.choices.temp_frame_quality_range))
    group_frame_extraction.add_argument('--keep-temp', help = wording.get('help.keep_temp'), action = 'store_true',    default = config.get_bool_value('frame_extraction.keep_temp'))
    # output creation
    group_output_creation = program.add_argument_group('output creation')
    group_output_creation.add_argument('--output-image-quality', help = wording.get('help.output_image_quality'), type = int, default = config.get_int_value('output_creation.output_image_quality', '80'), choices = facefusion.choices.output_image_quality_range, metavar = create_metavar(facefusion.choices.output_image_quality_range))
    group_output_creation.add_argument('--output-video-encoder', help = wording.get('help.output_video_encoder'), default = config.get_str_value('output_creation.output_video_encoder', 'libx264'), choices = facefusion.choices.output_video_encoders)
    group_output_creation.add_argument('--output-video-preset', help = wording.get('help.output_video_preset'), default = config.get_str_value('output_creation.output_video_preset', 'veryfast'), choices = facefusion.choices.output_video_presets)
    group_output_creation.add_argument('--output-video-quality', help = wording.get('help.output_video_quality'), type = int, default = config.get_int_value('output_creation.output_video_quality', '80'), choices = facefusion.choices.output_video_quality_range, metavar = create_metavar(facefusion.choices.output_video_quality_range))
    group_output_creation.add_argument('--output-video-resolution', help = wording.get('help.output_video_resolution'), default = config.get_str_value('output_creation.output_video_resolution'))
    group_output_creation.add_argument('--output-video-fps', help = wording.get('help.output_video_fps'), type = float)
    group_output_creation.add_argument('--skip-audio', help = wording.get('help.skip_audio'), action = 'store_true', default = config.get_bool_value('output_creation.skip_audio'))
    # frame processors
    available_frame_processors = list_directory('facefusion/processors/frame/modules')
    program = ArgumentParser(parents = [ program ], formatter_class = program.formatter_class, add_help = True)
    group_frame_processors = program.add_argument_group('frame processors')
    group_frame_processors.add_argument('--frame-processors', help = wording.get('help.frame_processors').format(choices = ', '.join(available_frame_processors)), default = config.get_str_list('frame_processors.frame_processors', 'face_swapper'), nargs = '+')
    for frame_processor in available_frame_processors:
        frame_processor_module = load_frame_processor_module(frame_processor)
        frame_processor_module.register_args(group_frame_processors)
    # uis
    available_ui_layouts = list_directory('facefusion/uis/layouts')
    group_uis = program.add_argument_group('uis')
    group_uis.add_argument('--ui-layouts', help = wording.get('help.ui_layouts').format(choices = ', '.join(available_ui_layouts)), default = config.get_str_list('uis.ui_layouts', 'default'), nargs = '+')
    return program
    # run(program)


def apply_args(program : ArgumentParser) -> None:
    args = program.parse_args()
    # general
    # facefusion.globals.source_paths = args.source_paths
    # facefusion.globals.target_path = args.target_path
    # facefusion.globals.output_path = normalize_output_path(facefusion.globals.source_paths, facefusion.globals.target_path, args.output_path)
    # misc
    facefusion.globals.skip_download = args.skip_download
    facefusion.globals.headless = args.headless
    facefusion.globals.log_level = args.log_level
    # execution
    # facefusion.globals.execution_providers = decode_execution_providers(args.execution_providers)
    facefusion.globals.execution_providers = [ 'CUDAExecutionProvider' ]
    # facefusion.globals.execution_thread_count = args.execution_thread_count
    facefusion.globals.execution_thread_count = multiprocessing.cpu_count() * 2
    # facefusion.globals.execution_queue_count = args.execution_queue_count
    facefusion.globals.execution_queue_count = 32
    # memory
    facefusion.globals.video_memory_strategy = args.video_memory_strategy
    facefusion.globals.system_memory_limit = args.system_memory_limit
    # face analyser
    facefusion.globals.face_analyser_order = args.face_analyser_order
    facefusion.globals.face_analyser_age = args.face_analyser_age
    facefusion.globals.face_analyser_gender = args.face_analyser_gender
    facefusion.globals.face_detector_model = args.face_detector_model
    if args.face_detector_size in facefusion.choices.face_detector_set[args.face_detector_model]:
        facefusion.globals.face_detector_size = args.face_detector_size
    else:
        facefusion.globals.face_detector_size = '640x640'
    facefusion.globals.face_detector_score = args.face_detector_score
    # face selector
    facefusion.globals.face_selector_mode = args.face_selector_mode
    facefusion.globals.reference_face_position = args.reference_face_position
    facefusion.globals.reference_face_distance = args.reference_face_distance
    facefusion.globals.reference_frame_number = args.reference_frame_number
    # face mask
    facefusion.globals.face_mask_types = args.face_mask_types
    facefusion.globals.face_mask_blur = args.face_mask_blur
    facefusion.globals.face_mask_padding = normalize_padding(args.face_mask_padding)
    facefusion.globals.face_mask_regions = args.face_mask_regions
    # frame extraction
    facefusion.globals.trim_frame_start = args.trim_frame_start
    facefusion.globals.trim_frame_end = args.trim_frame_end
    facefusion.globals.temp_frame_format = args.temp_frame_format
    facefusion.globals.temp_frame_quality = args.temp_frame_quality
    facefusion.globals.keep_temp = args.keep_temp
    # output creation
    facefusion.globals.output_image_quality = args.output_image_quality
    facefusion.globals.output_video_encoder = args.output_video_encoder
    facefusion.globals.output_video_preset = args.output_video_preset
    facefusion.globals.output_video_quality = args.output_video_quality
    if is_video(args.target_path):
        target_video_resolutions = create_video_resolutions(args.target_path)
        if args.output_video_resolution in target_video_resolutions:
            facefusion.globals.output_video_resolution = args.output_video_resolution
        else:
            target_video_resolution = detect_video_resolution(args.target_path)
            facefusion.globals.output_video_resolution = pack_resolution(target_video_resolution)
    if args.output_video_fps or is_video(args.target_path):
        facefusion.globals.output_video_fps = normalize_fps(args.output_video_fps) or detect_video_fps(args.target_path)
    facefusion.globals.skip_audio = args.skip_audio
    # frame processors
    available_frame_processors = list_directory('facefusion/processors/frame/modules')
    facefusion.globals.frame_processors = args.frame_processors
    for frame_processor in available_frame_processors:
        frame_processor_module = load_frame_processor_module(frame_processor)
        frame_processor_module.apply_args(program)
    # uis
    facefusion.globals.ui_layouts = args.ui_layouts
    print("-------------------------mod_param_begin--------------------------------")
    # print("source_paths", facefusion.globals.source_paths)
    # print("target_path", facefusion.globals.target_path)
    # print("output_path", facefusion.globals.output_path)
    print("skip_download", facefusion.globals.skip_download)
    print("headless", facefusion.globals.headless)
    print("log_level", facefusion.globals.log_level)
    print("execution_providers", facefusion.globals.execution_providers)
    print("execution_thread_count", facefusion.globals.execution_thread_count)
    print("execution_queue_count", facefusion.globals.execution_queue_count)
    print("video_memory_strategy", facefusion.globals.video_memory_strategy)
    print("system_memory_limit", facefusion.globals.system_memory_limit)
    print("face_analyser_order",facefusion.globals.face_analyser_order)
    print("face_analyser_age",facefusion.globals.face_analyser_age)
    print("face_analyser_gender",facefusion.globals.face_analyser_gender)
    print("face_detector_model",facefusion.globals.face_detector_model)
    print("face_detector_size",facefusion.globals.face_detector_size)
    print("face_detector_score",facefusion.globals.face_detector_score)
    print("face_selector_mode",facefusion.globals.face_selector_mode)
    print("reference_face_position",facefusion.globals.reference_face_position)
    print("reference_face_distance",facefusion.globals.reference_face_distance)
    print("reference_frame_number",facefusion.globals.reference_frame_number)
    print("face_mask_types",facefusion.globals.face_mask_types)
    print("face_mask_blur",facefusion.globals.face_mask_blur)
    print("face_mask_padding",facefusion.globals.face_mask_padding)
    print("face_mask_regions",facefusion.globals.face_mask_regions)
    print("trim_frame_start",facefusion.globals.trim_frame_start)
    print("trim_frame_end",facefusion.globals.trim_frame_end)
    print("temp_frame_format",facefusion.globals.temp_frame_format)
    print("temp_frame_quality",facefusion.globals.temp_frame_quality)
    print("keep_temp",facefusion.globals.keep_temp)
    print("output_image_quality",facefusion.globals.output_image_quality)
    print("output_video_encoder",facefusion.globals.output_video_encoder)
    print("output_video_preset",facefusion.globals.output_video_preset)
    print("output_video_quality",facefusion.globals.output_video_quality)
    print("output_video_resolution",facefusion.globals.output_video_resolution)
    print("output_video_fps",facefusion.globals.output_video_fps)
    print("skip_audio",facefusion.globals.skip_audio)
    print("frame_processors",facefusion.globals.frame_processors)
    print("ui_layouts",facefusion.globals.ui_layouts)
    print("-------------------------mod_param_end--------------------------------")

    

def run(program : ArgumentParser) -> None:
    # apply_args(program)
    logger.init(facefusion.globals.log_level)
    logger.info("-------------begin---------------")
    s = time.time()
    if facefusion.globals.system_memory_limit > 0:
        limit_system_memory(facefusion.globals.system_memory_limit)
    logger.info(f"limit_system_memory use time {round(time.time() - s, 2)}s")
    s = time.time()
    if not pre_check() or not content_analyser.pre_check() or not face_analyser.pre_check() or not face_masker.pre_check():
        return
    logger.info(f"pre_check use time {round(time.time() - s, 2)}s")
    s = time.time()
    for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
        if not frame_processor_module.pre_check():
            return
    logger.info(f"frame_processor_module use time {round(time.time() - s, 2)}s")
    s = time.time()
    if facefusion.globals.headless:
        conditional_process()
        logger.info(f"conditional_process use time {round(time.time() - s, 2)}s")
        s = time.time()
    else:
        import facefusion.uis.core as ui

        for ui_layout in ui.get_ui_layouts_modules(facefusion.globals.ui_layouts):
            if not ui_layout.pre_check():
                return
        ui.launch()
    logger.info("--------------end----------------")


def destroy() -> None:
    if facefusion.globals.target_path:
        clear_temp(facefusion.globals.target_path)
    sys.exit(0)


def pre_check() -> bool:
    if sys.version_info < (3, 9):
        logger.error(wording.get('python_not_supported').format(version = '3.9'), __name__.upper())
        return False
    if not shutil.which('ffmpeg'):
        logger.error(wording.get('ffmpeg_not_installed'), __name__.upper())
        return False
    return True


def conditional_process() -> None:
    start_time = time.time()
    s = time.time()
    for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
        while not frame_processor_module.post_check():
            logger.disable()
            sleep(0.5)
        logger.enable()
        if not frame_processor_module.pre_process('output'):
            return
    logger.info(f"post check frame_processors_modules use time {round(time.time() - s, 2)}s")
    s = time.time()
    conditional_append_reference_faces()
    logger.info(f"conditional_append_reference_faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    if is_image(facefusion.globals.target_path):
        process_image(start_time)
        logger.info(f"process_image use time {round(time.time() - s, 2)}s")
        s = time.time()
    if is_video(facefusion.globals.target_path):
        process_video(start_time)
        logger.info(f"process_video use time {round(time.time() - s, 2)}s")
        s = time.time()

# def model_process(img, tmplate, choose_type, paths, commpress) -> None:
def model_process(request_id, choose_type, path_info:path_config):
    start_time = time.time()
    s = time.time()
    conditional_append_reference_faces()
    logger.info(f"id:{request_id}, conditional_append_reference_faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    # 图片换脸
    if choose_type == E_CHOOSE_IMG:
        img_res = process_image(request_id, path_info, True)
        if img_res[CODE] != E_SUCESS[CODE]:
            return img_res
        logger.info(f"request_id:{request_id}, process_image use time {round(time.time() - s, 2)}s")
        s = time.time()
    else:
        video_res = process_video_new(request_id, path_info)
        if video_res[CODE] != E_SUCESS[CODE]:
            return video_res
        logger.info(f"request_id:{request_id}, process_video use time {round(time.time() - s, 2)}s")
    return E_SUCESS


def conditional_append_reference_faces(path_info:path_config, is_video_type) -> None:
    if 'reference' in facefusion.globals.face_selector_mode and not get_reference_faces():
        # source_frames = read_static_images(facefusion.globals.source_paths)
        source_frames = read_static_images(path_info.user_path_list)
        source_face = get_average_face(source_frames)
        # if is_video(facefusion.globals.target_path):
        if is_video_type:
            # reference_frame = get_video_frame(facefusion.globals.target_path, facefusion.globals.reference_frame_number)
            reference_frame = get_video_frame(path_info.template_video_path, facefusion.globals.reference_frame_number)
        else:
            # reference_frame = read_image(facefusion.globals.target_path)
            reference_frame = read_image(path_info.template_img_path)
        reference_face = get_one_face(reference_frame, facefusion.globals.reference_face_position)
        append_reference_face('origin', reference_face)
        if source_face and reference_face:
            for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
                abstract_reference_frame = frame_processor_module.get_reference_frame(source_face, reference_face, reference_frame, path_info.user_path_list[0])
                if numpy.any(abstract_reference_frame):
                    reference_frame = abstract_reference_frame
                    reference_face = get_one_face(reference_frame, facefusion.globals.reference_face_position)
                    append_reference_face(frame_processor_module.__name__, reference_face)

# path : user_path, template_path, output_path
def process_image(task_id, path_info:path_config, commpress):
    start_time = time.time()
    s = time.time()
    clear_reference_faces()
    clear_static_faces()
    logger.info(f"clear history faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    conditional_append_reference_faces(path_info, False)
    logger.info(f"id: {task_id}, conditional_append_reference_faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    shutil.copy2(path_info.template_img_path, path_info.output_img_path)
    # process frame
    for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
        logger.info(f"id: {task_id}, {wording.get('processing')} {frame_processor_module.NAME}")
        frame_processor_module.process_image(path_info.user_path_list, path_info.output_img_path, path_info.output_img_path)
        frame_processor_module.post_process()
    # compress image
    if commpress:
        ok, msg = compress_image(path_info.output_img_path)
        if not ok:
            logger.error(f"id: {task_id}, compress image error: {msg}")
        else:
            logger.info(f"id: {task_id}, {wording.get('compressing_image_succeed')}")
    seconds = '{:.2f}'.format((time.time() - start_time))
    logger.info(f"id: {task_id}, process img use time {seconds}s")
    return E_SUCESS


def process_video(start_time : float) -> None:
    if analyse_video(facefusion.globals.target_path, facefusion.globals.trim_frame_start, facefusion.globals.trim_frame_end):
        return
    logger.info(f"analyse_video use time {round(time.time() - s, 2)}s")
    s = time.time()
    # clear temp
    logger.debug(wording.get('clearing_temp'), __name__.upper())
    clear_temp(facefusion.globals.target_path)
    # create temp
    logger.debug(wording.get('creating_temp'), __name__.upper())
    create_temp(facefusion.globals.target_path)
    # extract frames
    logger.info(wording.get('extracting_frames_fps').format(video_fps = facefusion.globals.output_video_fps), __name__.upper())
    extract_frames(facefusion.globals.target_path, facefusion.globals.output_video_resolution, facefusion.globals.output_video_fps)
    logger.info(f"extract_frames use time {round(time.time() - s, 2)}s")
    s = time.time()
    # process frame
    temp_frame_paths = get_temp_frame_paths(facefusion.globals.target_path)
    if temp_frame_paths:
        for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
            logger.info(wording.get('processing'), frame_processor_module.NAME)
            frame_processor_module.process_video(facefusion.globals.source_paths, temp_frame_paths, [])
            frame_processor_module.post_process()
    else:
        logger.error(wording.get('temp_frames_not_found'), __name__.upper())
        return
    logger.info(f"process frame use time {round(time.time() - s, 2)}s")
    s = time.time()
    # merge video
    logger.info(wording.get('merging_video_fps').format(video_fps = facefusion.globals.output_video_fps), __name__.upper())
    if not merge_video(facefusion.globals.target_path, facefusion.globals.output_video_resolution, facefusion.globals.output_video_fps):
        logger.error(wording.get('merging_video_failed'), __name__.upper())
        return
    logger.info(f"merge video use time {round(time.time() - s, 2)}s")
    s = time.time()
    # handle audio
    if facefusion.globals.skip_audio:
        logger.info(wording.get('skipping_audio'), __name__.upper())
        move_temp(facefusion.globals.target_path, facefusion.globals.output_path)
    else:
        if 'lip_syncer' in facefusion.globals.frame_processors:
            source_audio_path = get_first(filter_audio_paths(facefusion.globals.source_paths))
            if source_audio_path and replace_audio(facefusion.globals.target_path, source_audio_path, facefusion.globals.output_path):
                logger.info(wording.get('restoring_audio_succeed'), __name__.upper())
            else:
                logger.warn(wording.get('restoring_audio_skipped'), __name__.upper())
                move_temp(facefusion.globals.target_path, facefusion.globals.output_path)
            logger.info(f"handle audio with lip_syncer use time {round(time.time() - s, 2)}s")
        else:
            if restore_audio(facefusion.globals.target_path, facefusion.globals.output_path, facefusion.globals.output_video_fps):
                logger.info(wording.get('restoring_audio_succeed'), __name__.upper())
            else:
                logger.warn(wording.get('restoring_audio_skipped'), __name__.upper())
                move_temp(facefusion.globals.target_path, facefusion.globals.output_path)
            logger.info(f"handle audio use time {round(time.time() - s, 2)}s")
    s = time.time()
    # clear temp
    logger.debug(wording.get('clearing_temp'), __name__.upper())
    clear_temp(facefusion.globals.target_path)
    # validate video
    if is_video(facefusion.globals.output_path):
        seconds = '{:.2f}'.format((time.time() - start_time))
        logger.info(wording.get('processing_video_succeed').format(seconds = seconds), __name__.upper())
    else:
        logger.error(wording.get('processing_video_failed'), __name__.upper())

def process_video_new(task_id, path_info:path_config):
    start_time = time.time()
    s = time.time()
    clear_reference_faces()
    clear_static_faces()
    logger.info(f"clear history faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    conditional_append_reference_faces(path_info, True)
    logger.info(f"id: {task_id}, conditional_append_reference_faces use time {round(time.time() - s, 2)}s")
    s = time.time()
    if not os.listdir(path_info.template_frame_path):
        logger.info(f"id: {task_id}, " + wording.get('extracting_frames_fps').format(video_fps = facefusion.globals.output_video_fps))
        extract_frames(path_info.template_video_path, path_info.template_frame_path, facefusion.globals.output_video_resolution, facefusion.globals.output_video_fps)
        logger.info(f"id: {task_id}, extract_frames use time {round(time.time() - s, 2)}s")
        s = time.time()
    # process frame
    temp_frame_paths = get_temp_frame_paths(path_info.template_video_path, path_info.template_frame_path)
    if temp_frame_paths:
        output_frame_paths = []
        output_dir_name = os.path.dirname(path_info.output_video_path)
        for temp_frame_path in temp_frame_paths:
            output_frame_paths.append(path_info.output_frame_path + '/' + os.path.basename(temp_frame_path))
        for frame_processor_module in get_frame_processors_modules(facefusion.globals.frame_processors):
            logger.info(wording.get('processing'), frame_processor_module.NAME)
            frame_processor_module.process_video(path_info.user_path_list, temp_frame_paths, output_frame_paths)
            frame_processor_module.post_process()
    else:
        logger.error(f'id: {task_id}, ' + wording.get('temp_frames_not_found'))
        return E_NOT_FIND_TEMPLATE_FRAMES
    logger.info(f"id: {task_id}, process frame use time {round(time.time() - s, 2)}s")
    s = time.time()
    # merge video
    logger.info(f"id: {task_id}, " + wording.get('merging_video_fps').format(video_fps = facefusion.globals.output_video_fps))
    merge_ok, merge_msg = merge_video(path_info.output_frame_path, path_info.output_video_no_audio_path, facefusion.globals.output_video_resolution, facefusion.globals.output_video_fps)
    if not merge_ok:
        logger.error(f"id: {task_id}, merge_video error: {merge_msg}")
        return E_MERGE_VIDEO_ERR
    logger.info(f"id: {task_id}, merge video use time {round(time.time() - s, 2)}s")
    s = time.time()
    # handle audio
    if facefusion.globals.skip_audio:
        logger.info("id: {task_id}, skip audio")
    else:
        # lip_syncer 视频替换视频处理 暂时不考虑
        if 'lip_syncer' in facefusion.globals.frame_processors:
            source_audio_path = get_first(filter_audio_paths(path_info.user_path_list))
            if source_audio_path and replace_audio(path_info.template_video_path, source_audio_path, path_info.output_video_path):
                logger.info(f"id: {task_id}, replace audio succeed use time {round(time.time() - s, 2)}")
            else:
                logger.error(f"id: {task_id}, replace audio error")
        else:
            audio_ok, audio_msg = restore_audio(path_info.template_video_path, path_info.output_video_no_audio_path, path_info.output_video_path, facefusion.globals.output_video_fps)
            if not audio_ok:
                logger.error(f"id: {task_id}, restore audio error: {audio_msg}")
                path_info.output_video_path = path_info.output_video_no_audio_path
            else:
                logger.info(f"id: {task_id}, restore audio succeed use time {round(time.time() - s, 2)}s")
    s = time.time()
    # validate video
    if not is_video(path_info.output_video_path):
        logger.error(f"id: {task_id}, processing video failed")
        return E_PROCESS_VIDEO_ERR
    # 清理用户frame目录
    shutil.rmtree(path_info.output_frame_path)
    seconds = '{:.2f}'.format((time.time() - start_time))
    logger.info(f"id: {task_id}, processing video succeed use time {seconds}s")
    return E_SUCESS