import pygame 
import sys 
pygame.init() 
pygame.display.set_mode((1, 1)) 
asset_paths = ['assets/Main Ship - Engines - Base Engine.png', 'assets/Main Ship - Engines - Burst Engine.png', 'assets/Main Ship - Weapons - Auto Cannon.png', 'assets/Main Ship - Weapons - Zapper.png'] 
for path in asset_paths: 
    try: 
        image = pygame.image.load(path) 
        width, height = image.get_size() 
        print(f"{path} | width: {width}, height: {height}") 
    except (pygame.error, FileNotFoundError): 
        print(f"{path} | File not found") 
pygame.quit() 
sys.exit() 
