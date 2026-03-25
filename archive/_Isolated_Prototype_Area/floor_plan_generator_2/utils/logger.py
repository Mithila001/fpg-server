# import logging

# def get_logger(name):
#     logger = logging.getLogger(name)
#     if not logger.handlers:
#         logger.setLevel(logging.DEBUG)
        
#         # Format: Time - Name of File - Status - Message
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
#         ch = logging.StreamHandler()
#         ch.setFormatter(formatter)
#         logger.addHandler(ch)
#     return logger