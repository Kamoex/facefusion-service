import os
from typing import List, Optional

from facefusion.typing import LogLevel, VideoMemoryStrategy, FaceSelectorMode, FaceAnalyserOrder, FaceAnalyserAge, FaceAnalyserGender, FaceMaskType, FaceMaskRegion, OutputVideoEncoder, OutputVideoPreset, FaceDetectorModel, FaceRecognizerModel, TempFrameFormat, Padding

# general
# source_paths : Optional[List[str]] = None
# target_path : Optional[str] = None
# output_path : Optional[str] = None
# misc
skip_download : Optional[bool] = True
headless : Optional[bool] = True
log_level : Optional[LogLevel] = 'info'
# execution
execution_providers : List[str] = []
execution_thread_count : Optional[int] = (os.cpu_count()) * 2
execution_queue_count : Optional[int] = 64
# memory
video_memory_strategy : Optional[VideoMemoryStrategy] = 'strict'
system_memory_limit : Optional[int] = None
# face analyser
face_analyser_order : Optional[FaceAnalyserOrder] = 'left-right'
face_analyser_age : Optional[FaceAnalyserAge] = None
face_analyser_gender : Optional[FaceAnalyserGender] = None
face_detector_model : Optional[FaceDetectorModel] = 'yoloface'
face_detector_size : Optional[str] = '640x640'
face_detector_score : Optional[float] = 0.5
face_recognizer_model : Optional[FaceRecognizerModel] = None
# face selector
face_selector_mode : Optional[FaceSelectorMode] = 'reference'
reference_face_position : Optional[int] = 0
reference_face_distance : Optional[float] = 0.6
reference_frame_number : Optional[int] = 0
# face mask
face_mask_types : Optional[List[FaceMaskType]] = ['box']
face_mask_blur : Optional[float] = 0.3
face_mask_padding : Optional[Padding] = (0, 0, 0, 0)
face_mask_regions : Optional[List[FaceMaskRegion]] = ['skin', 'left-eyebrow', 'right-eyebrow', 'left-eye', 'right-eye', 'eye-glasses', 'nose', 'mouth', 'upper-lip', 'lower-lip']
# frame extraction
trim_frame_start : Optional[int] = None
trim_frame_end : Optional[int] = None
temp_frame_format : Optional[TempFrameFormat] = "jpg"
temp_frame_quality : Optional[int] = 100
keep_temp : Optional[bool] = False
# output creation
output_image_quality : Optional[int] = 80
output_video_encoder : Optional[OutputVideoEncoder] = "libx264"
output_video_preset : Optional[OutputVideoPreset] = "veryfast"
output_video_quality : Optional[int] = 80
output_video_resolution : Optional[str] = "544x960"
output_video_fps : Optional[float] = 24.0
skip_audio : Optional[bool] = False
# frame processors
frame_processors : List[str] = ["face_swapper"]
# uis
ui_layouts : List[str] = []
