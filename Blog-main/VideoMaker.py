import time
import win32com.client
from win32com.client import constants as c
import os

class VideoMaker():
    item = ''
    images = []
    powerpoint = None

    def __init__(self, item, images=[]):
        self.item = item
        if len(images) == 0:
            # get images below the directory
            dir = f'C:/Utilities/Blog/images/{item}'
            images = [f'{dir}/{image}' for image in os.listdir(dir) if (not image.endswith('org.png') and not image.endswith('combined.png'))]
        self.images = images
        try:
            os.makedirs(f"C:/Utilities/Blog/video/{item}")
        except:
            pass
        
    def _init(self):
        self.powerpoint = win32com.client.gencache.EnsureDispatch("PowerPoint.Application")
    def __del__(self):
        if self.powerpoint is not None:
            self.powerpoint.Quit()
            self.powerpoint = None
    def make_video(self):
        video_file_path = f'C:/Utilities/Blog/video/{self.item}/{self.item}.mp4'
        # make ppt slide show with ffmpeg
        import subprocess
        if os.path.exists(video_file_path):
            print('File exists, skipping process.')
            return video_file_path
        option1 = ''.join([f'-loop 1 -t 4 -i "{image}" ' for image in self.images])
        option2 = ''.join([f'[{i}:v]fade=t=in:st=0:d=1,fade=t=out:st=3:d=1[v{i}]; ' for i in range(1, len(self.images))])
        option3 = ''.join([f'[v{i}]' for i in range(len(self.images))])
        ffmpeg_command = f'ffmpeg \
{option1} \
-filter_complex \
"[0:v]fade=t=out:st=3:d=1[v0]; \
 {option2} \
 {option3}concat=n={len(self.images)}:v=1:a=0,format=rgb24[v]" -map "[v]" "{video_file_path}"'
        print(ffmpeg_command)
        subprocess.Popen(ffmpeg_command)
        print('ffmpeg started')
        while not os.path.exists(video_file_path):
            time.sleep(1)
        print('ffmpeg completed')
        return video_file_path
        
    def make_video_win32(self):
        # make ppt slide show with win32com
        if self.powerpoint is None:
            self._init()
        presentation = self.powerpoint.Presentations.Add(1)
        
        for i, image in enumerate(self.images):
            print(image)
            slide = presentation.Slides.Add(i+1, 11)
            slide.Shapes.AddPicture(image.replace('/', '\\'), LinkToFile=False, SaveWithDocument=True, Left=230, Top=20, Width=500, Height=500)
            
        # convert to mp4 with win32com duration = 3000
        video_file_path = f'C:/Utilities/Blog/video/{self.item}/{self.item}_win32.mp4'
        presentation.CreateVideo(video_file_path, DefaultSlideDuration=3)
        while presentation.CreateVideoStatus == 1:
            time.sleep(10)
        presentation.Close()
        print('Video created successfully')
        
if __name__ == '__main__':
    # arguments to images
    import sys
    images = sys.argv[1:]
    
    maker = VideoMaker('온수 매트', images)
    maker.make_video()
    # maker.make_video_win32()