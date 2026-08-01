from models.job import Job


class JobFilter:

    EMBEDDED_KEYWORDS = [

        "embedded",
        "firmware",
        "embedded c",
        "embedded linux",
        "linux",
        "driver",
        "device driver",
        "bsp",
        "rtos",
        "freertos",
        "arm",
        "microcontroller",
        "mcu",
        "iot",
        "esp32",
        "stm32",
        "uart",
        "spi",
        "i2c",
        "electronics",
        "ece"

    ]


    LOCATION_KEYWORDS = [

        "hyderabad",
        "bangalore",
        "bengaluru",
        "chennai",
        "pune",
        "visakhapatnam",
        "vizag",
        "remote",
        "india"

    ]


    EXPERIENCE_KEYWORDS = [

        "fresher",
        "graduate",
        "0 year",
        "0-1",
        "entry",
        "trainee",
        "intern"

    ]


    def calculate_score(self, job: Job):

        text = (

            job.title +
            " " +
            job.company +
            " " +
            " ".join(job.skills)

        ).lower()


        score = 0


        for keyword in self.EMBEDDED_KEYWORDS:

            if keyword in text:
                score += 5


        location = job.location.lower()

        for place in self.LOCATION_KEYWORDS:

            if place in location:
                score += 2


        experience = job.experience.lower()

        for exp in self.EXPERIENCE_KEYWORDS:

            if exp in experience:
                score += 3


        if score > 100:
            score = 100


        return score



    def filter_jobs(self, jobs):

        matched_jobs = []


        for job in jobs:

            score = self.calculate_score(job)

            job.match_score = score


            if score >= 20:

                matched_jobs.append(job)


        return matched_jobs
