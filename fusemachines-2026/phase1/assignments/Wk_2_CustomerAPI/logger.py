import logging

logging.basicConfig(level= logging.INFO)


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s- %(name)s-%(levelname)s- %(message)s"

        )


        # log to file 
        file_Handler = logging.FileHandler('app.log')
        file_Handler.setFormatter(formatter)

        # log to terminal 
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)


        logger.addHandler(file_Handler)
        logger.addHandler(stream_handler)
    return logger

    




