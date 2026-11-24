from compiler.render.markdown import render


def test_single_paragraph_is_unwrapped():
    assert render("**Hello**") == ("<strong>Hello</strong>", set())


def test_multi_paragraph_kept():
    assert render("a\n\nb")[0] == "<p>a</p>\n<p>b</p>"


def test_image_rewritten_to_basename_and_collected():
    html, media = render("![carte](media/carte%20bordeaux.png)")
    assert 'src="carte bordeaux.png"' in html
    assert media == {"media/carte bordeaux.png"}


def test_image_angle_bracket_syntax():
    html, media = render("![](<media/a b.png>)")
    assert 'src="a b.png"' in html
    assert media == {"media/a b.png"}


def test_inline_html_img_rewritten():
    html, media = render('<img src="media/x.png">')
    assert 'src="x.png"' in html
    assert media == {"media/x.png"}


def test_non_media_src_untouched():
    html, media = render("![x](https://example.com/a.png)")
    assert 'src="https://example.com/a.png"' in html
    assert media == set()


def test_cloze_and_accents_survive():
    assert (
        render("La {{c1::Côte-d’Or}} & <b>Beaune</b>")[0]
        == "La {{c1::Côte-d’Or}} &amp; <b>Beaune</b>"
    )


def test_reference_style_image_collected():
    html, media = render("![x][r]\n\n[r]: media/../secret.txt")
    assert media == {"media/../secret.txt"}
    assert 'src="secret.txt"' in html


def test_local_non_media_paths_collected_but_not_rewritten():
    html, media = render('![a](img/a.png) <img src="/abs.png"> <img src="//cdn/x.png">')
    assert media == {"img/a.png", "/abs.png"}
    assert 'src="img/a.png"' in html
    assert 'src="/abs.png"' in html
