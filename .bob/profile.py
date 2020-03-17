from datetime import datetime


class Profile():

    class PlaceholderValue(object):

        def __init__(self, name, description, callback):
            self.name = name
            self.description = description
            self.element = lambda: callback()

    def __init__(self):
        self.placeholder_values = [
            Profile.PlaceholderValue("date", "current date %Y%m%d", lambda: datetime.now().strftime("%Y%m%d")),
            Profile.PlaceholderValue("date_time", "current date and time %Y%m%d%H%M%S", lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
        ]
