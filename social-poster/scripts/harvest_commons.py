import urllib.request, json, urllib.parse, time, re, os
# Set COMMONS_UA to a descriptive agent plus a contact URL or email, as the
# Wikimedia User-Agent policy requires.
UA={'User-Agent':os.environ['COMMONS_UA']}
API="https://commons.wikimedia.org/w/api.php?"
PERM=("cc0","public domain","cc by 2","cc by 3","cc by 4")
def api(p):
    for n in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(API+urllib.parse.urlencode(p),headers=UA),timeout=60))
        except Exception:
            if n==4: raise
            time.sleep(2.0*(n+1))
found=json.load(open("harvest.json")) if os.path.exists("harvest.json") else {}
cats=["National Hockey League games","Liiga","Ice hockey matches in Canada",
 "American Hockey League","Women's ice hockey","Ice hockey at the Winter Universiade",
 "NHL Winter Classic","Ice hockey at the 2006 Winter Olympics","Ice hockey in Sweden",
 "Ice hockey in Switzerland","Ice hockey in Norway",
 "Ice hockey in Denmark","Ice hockey in Slovakia","Ice hockey in Latvia","Ice hockey in Poland",
 "ECHL","NCAA ice hockey","Deutsche Eishockey Liga","Czech Extraliga","Ice hockey in Italy",
 "Ice hockey in Austria","Ice hockey in France","Ice hockey in Great Britain"]
for c in cats:
    try:
        d=api({"action":"query","format":"json","generator":"search","gsrsearch":f'deepcategory:"{c}" filetype:bitmap',
               "gsrnamespace":"6","gsrlimit":"500","prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":"600"})
    except Exception as e:
        print("ERR",c,e,flush=True); time.sleep(3); continue
    pages=d.get("query",{}).get("pages",{}); kept=0
    for p in pages.values():
        if "imageinfo" not in p: continue
        ii=p["imageinfo"][0]; em=ii.get("extmetadata",{})
        lic=em.get("LicenseShortName",{}).get("value","?")
        w,h=ii.get("width",0),ii.get("height",0)
        if w<2000 or not h or w/h<1.2: continue
        if not lic.lower().startswith(PERM): continue
        if p["title"] in found: continue
        # Capture the shooting year here: the recency gate needs it, and refetching
        # extmetadata for the whole harvest afterwards costs another full API pass.
        raw=em.get("DateTimeOriginal",{}).get("value","") or em.get("DateTime",{}).get("value","")
        m=re.search(r"(?:19|20)\d\d", re.sub(r"<[^>]+>","",str(raw)))
        found[p["title"]]={"lic":lic,"thumb":ii.get("thumburl"),"page":ii.get("descriptionurl"),
                           "w":w,"h":h,"author":em.get("Artist",{}).get("value","")[:150],
                           "year":int(m.group(0)) if m else None}
        kept+=1
    print(f"{c[:42]:42s} {len(pages):4d} -> +{kept}  (total {len(found)})",flush=True)
    json.dump(found, open("harvest.json","w"))
    time.sleep(1.0)
print("HARVEST", len(found))
