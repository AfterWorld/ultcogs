"""Small bot-wide deck index search helper."""


def search_decks(posts, filters):
    terms = filters.casefold().split()
    if len(filters) > 150:
        raise ValueError('Keep the search under 150 characters.')
    pages = [term[5:] for term in terms if term.startswith('page:')]
    try:
        page = int(pages[-1]) if pages else (int(terms[0]) if len(terms) == 1 and terms[0].isdigit() else 1)
    except ValueError as exc:
        raise ValueError('Use `page:2` to choose a page.') from exc
    authors = [term[7:] for term in terms if term.startswith('author:')]
    keywords = [term for term in terms if not term.startswith(('author:', 'page:')) and not (len(terms) == 1 and term.isdigit())]
    results = []
    for post in reversed(posts):
        author = post.get('author_name', '').casefold()
        searchable = ' '.join((post.get('title', ''), post.get('attribute') or '', post.get('search_text', ''))).casefold()
        if all(value in author for value in authors) and all(value in searchable for value in keywords):
            results.append(post)
    return results, page
