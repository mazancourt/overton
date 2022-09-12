from collections import Counter, defaultdict

from actors import PersonName
from hedwige_utils import sanitize


def tag_person_names(speech, categorizer, namer, by_paragraphs=False):
    """
    Annotate each sentence with person names identified in it
    Try to unify person names, with variation on accents or omission of first name
    :param speech: the speech data
    :param categorizer: the NLP engine
    :param namer: the name parser
    :param by_paragraphs: work at paragraph-level, else at sentence  level (legacy version)
    :return: Nothing
    """

    if by_paragraphs:
        name = "paragraphs"
    else:
        name = "sentences"
    normalized_person_names = dict()
    bylastname = defaultdict(set)
    for sentence in speech[name]:
        sent_persons = categorizer.extract_persons(sentence["text"])
        sent_person_names = []
        for person in sent_persons.keys():
            if "\n" in person:  # frequent bug in SpaCy NER
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
    for sentence in speech[name]:
        sentence["persons"] = []
        if "person_names" in sentence:
            for person_name in sentence["person_names"]:
                p = normalized_person_names[person_name]
                if p in merge_to_person:
                    p = merge_to_person[p]
                if p.first_name and p.last_name:    # don't care about incomplete names
                    sentence["persons"].append({"first_name": p.first_name, "last_name": p.last_name})
                    all_persons[p] += 1
            del sentence["person_names"]
    if not by_paragraphs:
        speech["meta"]["persons"] = []
        for p, c in all_persons.most_common():
            speech["meta"]["persons"].append({"first_name": p.first_name, "last_name": p.last_name, "count": c})


def attribute_paragraphs(paragraphs):
    """
    Compute attribution for a document split in paragraphs - each paragraph is tagged with a 'speaking' value
    :param paragraphs: the paragraph
    :return: the list of all persons detected as speakers for at least one paragraph
    """
    last_attribution = None
    doc_persons = set()
    for para in paragraphs:
        if "persons" in para:
            persons = [PersonName(p["first_name"], p["last_name"]) for p in para["persons"]]
            if len(persons) == 1:
                para["speaking"] = persons[0].full_name
                last_attribution = persons[0]
                doc_persons.add(persons[0])
            elif len(persons) > 1:
                para["speaking"] = None
                last_attribution = None
            else:
                para["speaking"] = last_attribution.full_name if last_attribution else None
        else:
            para["speaking"] = last_attribution.full_name if last_attribution else None
    return [p.full_name for p in doc_persons]
