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


def parse_students(csv, parent_map):
    with open(csv, "r") as f:
        lines = f.readlines()

    ret = []

    for line in lines:
        if line.startswith("Course,"):
            class_string = line.strip().split(",")[-1]
            section = class_string.split()[-1]

        if not re.match("^\d+,", line):
            continue

        _, sid, last_name, first_name, _, _ = line.strip().split(",", maxsplit=5)
        sid = sid.replace("-", "")
        cn, email = parent_map[sid]

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
        print(org.name)
        print(org.slug)
        print(org.short_name)
        print(org.registrant)
        print()
        print(class_title)
        print(slug)
        input("Press ENTER to confirm: ")
        if org.name != class_title or \
                org.slug != slug or \
                org.short_name != class_title or \
                org.registrant != handlers[0]:
            print("Organization must be updated")
            org.name = class_title
            org.slug = slug
            org.short_name = class_title
            org.registrant = handlers[0]
            org.save()
    else:
        print("Creating organization for", slug)
        input("Press ENTER to confirm: ")
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


def parse_parent_map(csvs):
    ret = {}

    for csv in csvs:
        with open(csv, "r") as f:
            lines = f.readlines()

        for line in lines:
            if not re.match("^\d+,", line):
                continue

            cn, sid, _, _, _, email = line.strip().split(",", maxsplit=5)
            sid = sid.replace("-", "")

            ret[sid] = (cn, email)

    return ret


def init_single_class(class_title, csv, org_slug, language_name, handlers=['jfmcoronel'], parent_org=None, parent_csvs=None):
    handlers = get_profiles(handlers)
    lang = Language.objects.get(name=language_name)
    org = get_or_init_org(class_title, org_slug, handlers)

    new_accounts = []
    existing_accounts = []

    if not parent_csvs:
        parent_csvs = [csv]
    parent_map = parse_parent_map(parent_csvs)

    for student in parse_students(csv, parent_map):
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
        if parent_org:
            profile.organizations.add(parent_org)
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
    output_lines = []
    for new_account in new_accounts:
        output_line = ",".join([
            new_account.student.display_name,
            new_account.student.sid,
            new_account.password,
            new_account.student.email,
        ])

        print(output_line)
        output_lines.append(output_line)

    with open(f"{csv}.passwords.txt", "w") as f:
        f.writelines(output_lines)


def init_parent_child_classes(class_title, org_slug, language_name, emails, csvs, handlers=['jfmcoronel']):
    profiles = get_profiles(handlers)
    parent_org = get_or_init_org(class_title, org_slug, profiles)

    for csv in sorted(csvs):
        # FIXME: Hardcoded assumptions
        semester = class_title.split()[-1]
        lab_title = csv.split("/")[1].split("_")[0]
        course_name, section = lab_title.rsplit(maxsplit=1)
        lab_slug = course_name.replace(' ', '') + semester.replace('.', '') + \
            section.replace('-', '')
        lab_slug = lab_slug.lower()

        init_single_class(lab_title, csv, lab_slug, language_name, handlers, parent_csvs=emails)


def main():
    init_parent_child_classes(
        "CS 11 20.1",
        "cs11201",
        "Python 3",
        [
            "@scripts/CS 11 A_studentcontactlist.csv",
            "@scripts/CS 11 B_studentcontactlist.csv",
        ],
        [
            "@scripts/CS 11 A-1_classlist.csv",
            "@scripts/CS 11 A-2_classlist.csv",
            "@scripts/CS 11 A-3_classlist.csv",
            "@scripts/CS 11 A-4_classlist.csv",
            "@scripts/CS 11 A-5_classlist.csv",
            "@scripts/CS 11 B-1_classlist.csv",
            "@scripts/CS 11 B-2_classlist.csv",
            "@scripts/CS 11 B-3_classlist.csv",
            "@scripts/CS 11 B-4_classlist.csv",
            "@scripts/CS 11 B-5_classlist.csv",
        ],
        ["pczuniga", "rsgabud", "hapaat"],
    )

    """
    init_parent_child_classes(
        "CS 32 20.1",
        "cs32201",
        "C",
        [
            "@scripts/CS 32 THY_studentcontactlist.csv",
            "@scripts/CS 32 A_studentcontactlist.csv",
            "@scripts/CS 32 B_studentcontactlist.csv",
        ],
        [
            "@scripts/CS 32 A_classlist.csv",
            "@scripts/CS 32 B_classlist.csv",
            "@scripts/CS 32 C_classlist.csv",
            "@scripts/CS 32 D_classlist.csv",
            "@scripts/CS 32 F_classlist.csv",
        ],
        ["pczuniga", "rbjuayong", "kcbuno"],
    )
    """

    # init_single_class(
    #     "CS 12 20.1",
    #     "@scripts/CS 12 THUV_studentcontactlist.csv",
    #     "cs12201",
    #     "Python 3",
    #     ['jbbeltran'],
    # )


main()  # Do not use __main__
        # exec(open("@scripts/init_users_from_csv.py").read())
