import os
import sys
import re
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


def init_single_class(class_title, csv, org_slug, language_name, handlers=['jfmcoronel']):
    handlers = get_profiles(handlers)
    lang = Language.objects.get(name=language_name)
    org = get_or_init_org(class_title, org_slug, handlers)

    for student in parse_csv(csv):
        display_name = f"{student.cn}_{student.section}_{student.last_name}_{student.first_name}"

        filtered = User.objects.filter(username=student.sid)
        if not filtered:
            print("No user yet for", display_name)
        else:
            profile = Profile.objects.filter(user=filtered[0]).first()
            if not profile:
                print("Adding profile for", display_name)
                # new_prof, created = Profile.objects.create(user=us, language=lang, name=display_name)

            print("Updating profile for", display_name)
            profile.organizations.add(org)
            profile.name = display_name
            profile.save()


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

#with open("cs12201.txt", "r") as f:
#    data = f.readlines()
#    for line in data:
#        sid, display_name = line.strip().split(",")
#        email = sid + "@oj.dcs.upd.edu.ph"
#        filtered = User.objects.filter(username=sid)
#        if len(filtered) == 0:
#            print("No user yet for ", display_name)
#        else:
#            us = filtered[0]
#            profile = Profile.objects.filter(user=us)
#            if len(profile) == 0:
#                print("Adding profile for: ", display_name)
#                new_prof, created = Profile.objects.create(user=us, language=lang, name=display_name)
#                new_prof.organizations.add(cs12191)
#            else:
#                profile[0].organizations.add(cs12191)
#                profile[0].name = display_name
#                profile[0].save()
#
