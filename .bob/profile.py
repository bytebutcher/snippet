from datetime import datetime


class Profile():

    class PlaceholderValue(object):

        def __init__(self, description, callback):
            self.description = description
            self.callback = callback

        def getElement(self):
            return self.callback()

    date = PlaceholderValue("current date %Y%m%d", lambda: datetime.now().strftime("%Y%m%d"))
    date_time = PlaceholderValue("current date and time %Y%m%d%H%M%S", lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
