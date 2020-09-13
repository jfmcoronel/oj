import os
import sys
import re
import random
from dataclasses import dataclass

from judge.models import *
from django.contrib.auth.models import User


@dataclass
class StudentRow:
    cn: str
    sid: str
    last_name: str
    first_name: str
    email: str
    section: str
    display_name: str


@dataclass
class NewAccount:
    student: StudentRow
    password: str


def parse_csv(csv):
    with open(csv, "r") as f:
        lines = f.readlines()

    ret = []

    for line in lines:
        if line.startswith("Course,"):
            class_string = line.strip().split(",")[-1]
            section = class_string.split()[-1]

        if not re.match("^\d+,", line):
            continue

        cn, sid, last_name, first_name, _, email = line.strip().split(",")
        sid = sid.replace("-", "")

        ret.append(StudentRow(
                cn=cn,
                sid=sid,
                last_name=last_name,
                first_name=first_name,
                email=email,
                section=section,
                display_name=f"{cn}_{section}_{last_name}_{first_name}",
            ))

    return ret


def get_profiles(usernames):
    return [Profile.objects.get(user__username=username) for username in usernames]


def get_or_init_org(class_title, slug, handlers):
    org = Organization.objects.filter(slug=slug).first()
    if org:
        print("Organization", slug, "exists")
    else:
        print("Creating organization for", slug)
        org = Organization(
                name=class_title,
                slug=slug,
                short_name=class_title,
                registrant=handlers[0],
                is_open=False,
            )
        org.save()
        org.admins.set(handlers)

    return org


def _get_random(words):
    while True:
        word = random.choice(words).strip()

        if len(word) <= 8:
            return word


def generate_new_password():
    nouns = "@scripts/nouns.txt"
    adjectives = "@scripts/adjectives.txt"
    verbs = "@scripts/verbs.txt"

    with open(nouns) as f_nouns, open(adjectives) as f_adjectives, open(verbs) as f_verbs:
        verb = _get_random(f_verbs.readlines())
        adj = _get_random(f_adjectives.readlines())
        noun = _get_random(f_nouns.readlines())

    return f"{verb}-{adj}-{noun}"


def create_new_account(student):
    new = NewAccount(
            student=student,
            password=generate_new_password(),
        )

    user = User.objects.create_user(student.sid, student.email, new.password)

    return user, new


def init_single_class(class_title, csv, org_slug, language_name, handlers=['jfmcoronel']):
    handlers = get_profiles(handlers)
    lang = Language.objects.get(name=language_name)
    org = get_or_init_org(class_title, org_slug, handlers)

    new_accounts = []
    existing_accounts = []

    for student in parse_csv(csv):
        user = User.objects.filter(username=student.sid).first()
        if user:
            existing_accounts.append(student)
        else:
            print("Adding new user account for", student.display_name)
            user, new = create_new_account(student)
            new_accounts.append(new)
            continue

        profile = Profile.objects.filter(user=user).first()
        if not profile:
            print("Adding profile for", student.display_name)
            profile = Profile.objects.create(user=user, language=lang)

        print("Updating profile and last name for", student.display_name)
        profile.organizations.add(org)
        profile.save()
        user.last_name = student.display_name
        user.save()

    print(f"\nExisting accounts ({len(existing_accounts)})")
    for existing in existing_accounts:
        print(",".join([
            existing.display_name,
            existing.sid,
            existing.email,
        ]))

    print(f"\nNew accounts ({len(new_accounts)})")
    for new_account in new_accounts:
        print(",".join([
            new_account.student.display_name,
            new_account.student.sid,
            new_account.password,
            new_account.student.email,
        ]))


def main():
    init_single_class(
        "CS 12 20.1",
        "@scripts/CS 12 THUV_studentcontactlist.csv",
        "cs12201",
        "Python 3",
        ['jbbeltran'],
    )


main()  # Do not use __main__
        # exec(open("@scripts/init_users_from_csv.py").read())
