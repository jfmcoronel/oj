from django.conf import settings
from django.core.management.base import BaseCommand
from moss import *

from judge.models import Contest, ContestParticipation, Submission, Problem


class Command(BaseCommand):
    help = 'Checks for duplicate code using MOSS'

    LANG_MAPPING = {
        ('C++', MOSS_LANG_CC),
        ('C', MOSS_LANG_C),
        ('Java', MOSS_LANG_JAVA),
        ('Py3', MOSS_LANG_PYTHON),
    }

    def add_arguments(self, parser):
        parser.add_argument('problem_id', help='the id of the problem')

    def handle(self, *args, **options):
        moss_api_key = settings.MOSS_API_KEY
        if moss_api_key is None:
            print('No MOSS API Key supplied')
            return
        problem_id = options['problem_id']

        urls = []

        problems = Problem.objects.filter(code__startswith=problem_id)
        for problem in problems:
            print('========== %s / %s ==========' % (problem.code, problem.name))
            for dmoj_lang, moss_lang in self.LANG_MAPPING:
                print("%s: " % dmoj_lang, end=' ')
                subs = Submission.objects.filter(
                    problem=problem,
                    language__common_name=dmoj_lang,
                ).values_list('user__user__username', 'user__user__last_name', 'source__source')

                if not subs:
                    print('<no submissions>')
                    continue

                moss_call = MOSS(moss_api_key, language=moss_lang, matching_file_limit=100,
                                 comment='%s - %s' % (problem.code, problem.name))

                users = set()

                for username, codename, source in subs:
                    unique_name = f"{username} ({codename})"
                    if unique_name in users:
                        continue
                    users.add(unique_name)
                    moss_call.add_file_from_memory(unique_name, source.encode('utf-8'))

                count = subs.count()
                moss_output = moss_call.process()
                output = '%s - %s - (%d): %s' % (problem.code, problem.name, count, moss_output)
                print(output)

                urls.append(output)

        print("---")
        print("Links:")
        for url in urls:
            print(url)
