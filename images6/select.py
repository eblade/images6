from .entry import EntryQuery, get_entries


def select(args):
    params = {}
    fields = []
    separator = ';'
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            if key == 'separator':
                separator = value
            params[key] = value
        else:
            fields.append(arg)

    query = EntryQuery(**params)

    for entry in get_entries(query).entries:

        def f(entry, field):
            if ':' in field:
                function, args = field.split(':', 1)
                args = args.split(',')
                return getattr(entry, function)(*args)
            else:
                return getattr(entry, field)

        yield separator.join([str(f(entry, field)) for field in fields])
