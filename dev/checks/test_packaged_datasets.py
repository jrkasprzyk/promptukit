from importlib import resources
import promptukit as pk


def _iter_json_files(trav):
    for item in trav.iterdir():
        if item.is_dir():
            yield from _iter_json_files(item)
        else:
            if item.name.endswith(".json"):
                yield item


def test_packaged_question_banks_loads_json():
    data_root = resources.files("promptukit").joinpath("data")
    qb_root = data_root.joinpath("question_banks")
    assert qb_root.is_dir(), "promptukit/data/question_banks is missing from package"

    files = list(_iter_json_files(qb_root))
    assert files, "No JSON files found in promptukit/data/question_banks"

    for f in files:
        # load via the public helper; for files directly under question_banks
        # passing the bare filename is supported by pk.load_resource()
        obj = pk.load_resource(f.name)
        assert isinstance(obj, (dict, list)), f"Packaged file {f.name!r} did not load as JSON"
