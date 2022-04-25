from collections import Counter, defaultdict
from hedwige_utils import sanitize


def tag_person_names(speech, categorizer, namer):
    """
    Annotate each sentence with person names identified in it
    Try to unify person names, with variation on accents or omission of first name
    :param speech: the speech data
    :param categorizer: the NLP engine
    :return: Nothing
    """

    normalized_person_names = dict()
    bylastname = defaultdict(set)
    for sentence in speech["sentences"]:
        sent_persons = categorizer.extract_persons(sentence["text"])
        sent_person_names = []
        for person in sent_persons.keys():
            if "\n" in person: # frequent bug in SpaCy NER
                continue
            p = namer.parse(person)
            if p.last_name:
                bylastname[p.last_name].add(p)
                normalized_person_names[person] = p
                sent_person_names.append(person)
        sentence["person_names"] = sent_person_names

    merge_to_person = dict()
    # iterate over the persons with the same last name, check if we can unify person names
    for lastname, candidates in bylastname.items():
        if len(candidates) > 1:
            # there are possible merges
            byfirstname = defaultdict(set)
            for candidate in candidates:
                byfirstname[sanitize(candidate.first_name)].add(candidate)
            if len(byfirstname) == 1:
                target = candidates.pop()
            elif len(byfirstname) == 2 and "" in byfirstname:
                target = [p for p in candidates if p.first_name != ""][0]
            else:
                # Ambiguity - don't choose (?)
                target = None
            if target:
                for candidate in candidates:
                    merge_to_person[candidate] = target
    # finally normalize person names for each sentence using whole document
    # (cf. M. Macron -> Emmanuel Macron if both forms are present)
    all_persons = Counter()
    for sentence in speech["sentences"]:
        sentence["persons"] = []
        if "person_names" in sentence:
            for person_name in sentence["person_names"]:
                p = normalized_person_names[person_name]
                if p in merge_to_person:
                    p = merge_to_person[p]
                sentence["persons"].append({"first_name": p.first_name, "last_name": p.last_name})
                all_persons[p] += 1
            del sentence["person_names"]
    speech["meta"]["persons"] = []
    for p, c in all_persons.most_common():
        speech["meta"]["persons"].append({"first_name": p.first_name, "last_name": p.last_name, "count": c})

