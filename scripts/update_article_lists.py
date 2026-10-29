#!/usr/bin/env python3
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re, subprocess

START = "<!-- AUTO-ARTICLES-START -->"
END = "<!-- AUTO-ARTICLES-END -->"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.title, self.category = {}, [], []
        self.in_title, self.eyebrow_depth = False, 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key and attrs.get("content"): self.meta[key] = attrs["content"].strip()
        elif tag == "title": self.in_title = True
        elif tag in {"p", "div", "span"}:
            if not self.category and "eyebrow" in attrs.get("class", "").split():
                self.eyebrow_depth = 1
            elif self.eyebrow_depth: self.eyebrow_depth += 1
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        elif self.eyebrow_depth and tag in {"p", "div", "span"}: self.eyebrow_depth -= 1
    def handle_data(self, data):
        if self.in_title: self.title.append(data)
        if self.eyebrow_depth: self.category.append(data)

def modified(path):
    r = subprocess.run(["git","log","-1","--format=%ct","--",path.name],capture_output=True,text=True)
    try: return int(r.stdout.strip())
    except ValueError: return 0

def get_articles():
    result = []
    for path in Path(".").glob("*.html"):
        if path.name in {"index.html","articoli.html"}: continue
        try: source = path.read_text(encoding="utf-8")
        except (OSError,UnicodeDecodeError): continue
        p = Parser(); p.feed(source)
        if p.meta.get("og:type","").lower() != "article": continue
        title = p.meta.get("og:title") or " ".join(p.title)
        title = re.sub(r"\s*\|\s*Marco Palmas\s*$","",title).strip()
        category = " ".join(" ".join(p.category).split()).strip(" ·|") or "Articoli"
        result.append({"path":path.name,"title":title,"category":category,
          "description":p.meta.get("og:description") or p.meta.get("description",""),
          "date":modified(path)})
    return sorted(result,key=lambda x:(x["date"],x["path"]),reverse=True)

def replace_cards(source, generated):
    pattern = re.compile(re.escape(START)+r".*?"+re.escape(END),re.S)
    replacement = START+"\n"+generated.rstrip()+"\n                "+END
    updated, count = pattern.subn(lambda _:replacement,source,count=1)
    if count != 1: raise RuntimeError("Marker automatici mancanti o duplicati")
    return updated

def home_cards(items):
    return "\n\n".join(f'''                <a class="article-card" href="{escape(a["path"],quote=True)}">
                    <div>
                        <p class="article-category">{escape(a["category"])}</p>
                        <h3>{escape(a["title"])}</h3>
                    </div>
                    <span class="read-more">Leggi l'articolo →</span>
                </a>''' for a in items[:4])

def listing_cards(items):
    cards=[]
    for i,a in enumerate(items):
        cls="article-card article-main" if i==0 else "article-card article-secondary"
        cards.append(f'''            <article class="{cls}">
                <div>
                    <div class="category">{escape(a["category"])}</div>
                    <h2>{escape(a["title"])}</h2>
                    <p>{escape(a["description"])}</p>
                    <a href="{escape(a["path"],quote=True)}" class="read-more">Leggi l'articolo →</a>
                </div>
            </article>''')
    return "\n\n".join(cards) if cards else "            <p>Gli articoli saranno disponibili a breve.</p>"

def main():
    items=get_articles()
    if not items: raise RuntimeError("Nessun articolo pubblicato rilevato; nessun file modificato.")
    for name,html in (("index.html",home_cards(items)),("articoli.html",listing_cards(items))):
        path=Path(name); old=path.read_text(encoding="utf-8"); new=replace_cards(old,html)
        if new != old: path.write_text(new,encoding="utf-8"); print("Aggiornato",name)
        else: print(name,"già aggiornato")
    print("Articoli rilevati:",len(items))
if __name__=="__main__": main()
