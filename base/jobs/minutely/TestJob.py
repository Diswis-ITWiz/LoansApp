from django_extensions.management.jobs import BaseJob, MinutelyJob


class Job(MinutelyJob):
    help = "My sample job."

    def execute(self):
        print('Testing')
        # executing empty sample job
        pass
