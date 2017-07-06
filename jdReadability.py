# -*- coding: utf-8 -*-
#jdParser Arc90's Readability.js python port
#Akshat Joshi
import urllib2
import re
from bs4 import BeautifulSoup
import math
import sys
reload(sys)  
sys.setdefaultencoding('utf8')
url=raw_input('enter url : ')
urlO=urllib2.urlopen(url)
soup=BeautifulSoup(urlO,'html.parser')

candidates={}
  
regexps = {
        'unlikelyCandidates': re.compile("combx|comment|community|disqus|extra|foot|header|menu|"
                                         "remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|"
                                         "pagination|pager|popup|tweet|twitter",re.I),
        'MaybeCandidate': re.compile("and|article|body|column|main|shadow", re.I),
        'positive': re.compile("article|body|content|entry|hentry|main|page|pagination|post|text|"
                               "blog|story",re.I),
        'negative': re.compile("combx|comment|com|contact|foot|footer|footnote|masthead|media|"
                               "meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|"
                               "shopping|tags|tool|widget", re.I),
       'divToPElements': re.compile("<(a|blockquote|dl|div|img|ol|p|pre|table|ul)",re.I),
        'killBreaks': re.compile("(<br\s*/?>(\s|&nbsp;?)*)+",re.I),
        'videos': re.compile("http://(www\.)?(youtube|vimeo)\.com",re.I)
               }
def remScript():
    for elem in soup.find_all("script"):
        elem.extract()

def remStyle():
    for elem in soup.find_all("style"):
        elem.extract()
def remLink():
    for elem in soup.find_all("link"):
        elem.extract()
# Grab the title from the page.
def getArticleTitle():
    title = ''
    try:
        title = soup.find('title').text
    except:
        pass

    return title

# Study all the paragraphs and find the chunk that has the best score.
# A score is calculated by things like: Weight of classes and id's, Number of <p>'s, commas, etc.
def getArticle():
    for elem in soup.find_all(True):
        
        
            unlikelyMatchString = elem.get('id','')+''.join(elem.get('class',''))

            if  regexps['unlikelyCandidates'].search(unlikelyMatchString) and \
                not regexps['MaybeCandidate'].search(unlikelyMatchString) and \
                elem.name != 'body':
#                print elem
#                print '--------------------'
                elem.extract()
                continue
#                pass

            if elem.name == 'div':
                s = elem.encode_contents()
                if not regexps['divToPElements'].search(s.decode()):
                    elem.name = 'p'

    for node in soup.find_all('p'):
        parentNode = node.parent
        grandParentNode = parentNode.parent
        innerText = node.text

#            print '=================='
#            print node
#            print '------------------'
#            print parentNode

        if not parentNode or len(innerText) < 20:
            continue

        parentHash = hash(str(parentNode))
        grandParentHash = hash(str(grandParentNode))

        if parentHash not in candidates:
            candidates[parentHash] = initializeNode(parentNode)

        if grandParentNode and grandParentHash not in candidates:
            candidates[grandParentHash] = initializeNode(grandParentNode)

        contentScore = 1
        
        contentScore += innerText.count(',')    #Add one point to score for a comma found in paragraph
        contentScore +=  min(math.floor(len(innerText) / 100), 3) #Add points to score for the length of paragraph 

        candidates[parentHash]['score'] += contentScore

#            print '======================='
#            print self.candidates[parentHash]['score']
#            print self.candidates[parentHash]['node']
#            print '-----------------------'
#            print node

        if grandParentNode:
            
            candidates[grandParentHash]['score'] += contentScore / 2

    topCandidate = None

    for key in candidates:
            #            print '======================='
            #            print self.candidates[key]['score']
            #            print self.candidates[key]['node']

        candidates[key]['score'] = candidates[key]['score'] * (1 - getLinkDensity(candidates[key]['node']))

        if not topCandidate or candidates[key]['score'] > topCandidate['score']:
            topCandidate = candidates[key]

    content = ''

    if topCandidate:
        content = topCandidate['node']
#        print content
        content = cleanArticle(content)
    return content
    
# calls cleaning methods
def cleanArticle(content):
    cleanStyle(content)
    clean(content, 'h1')
    clean(content, 'object')
    cleanConditionally(content, "form")

    if len(content.find_all('h2')) == 1:
        clean(content, 'h2')

    clean(content, 'iframe')
    cleanConditionally(content, "table")
    cleanConditionally(content, "ul")
    cleanConditionally(content, "div")

    content = content.encode_contents()

    content = regexps['killBreaks'].sub("<br />", content.decode())

    return content
    
#remove plugins
def clean(e ,tag):
    targetList = e.find_all(tag)
    isEmbed = 0
    if tag =='object' or tag == 'embed':
        isEmbed = 1

    for target in targetList:
        attributeValues = ""
        for attribute in target.attrs:
                #
            get_attr = target.get(attribute[0])
            attributeValues += get_attr if get_attr is not None else ''

        if isEmbed and regexps['videos'].search(attributeValues):
            continue

        if isEmbed and regexps['videos'].search(target.encode_contents().decode()):
            continue
        target.extract()

def cleanStyle(e):
    for elem in e.find_all(True):
        del elem['class']
        del elem['id']
        del elem['style']

#clean on basis of node weights and scores
def cleanConditionally(e, tag):
    tagsList = e.find_all(tag)

    for node in tagsList:
        weight = getClassWeight(node)
        hashNode = hash(str(node))
        if hashNode in candidates:
            contentScore = candidates[hashNode]['score']
        else:
            contentScore = 0

        if weight + contentScore < 0:
            node.extract()
        else:
            p = len(node.find_all("p"))
            img = len(node.find_all("img"))
            li = len(node.find_all("li"))-100
            input_html = len(node.find_all("input_html"))
            embedCount = 0
            embeds = node.find_all("embed")
            for embed in embeds:
                if not regexps['videos'].search(embed['src']):
                    embedCount += 1
            linkDensity = getLinkDensity(node)
            contentLength = len(node.text)
            toRemove = False

            if img > p:
                toRemove = True
            elif li > p and tag != "ul" and tag != "ol":
                toRemove = True
            elif input_html > math.floor(p/3):
                toRemove = True
            elif contentLength < 25 and (img==0 or img>2):
                toRemove = True
            elif weight < 25 and linkDensity > 0.2:
                toRemove = True
            elif weight >= 25 and linkDensity > 0.5:
                toRemove = True
            elif (embedCount == 1 and contentLength < 35) or embedCount > 1:
                toRemove = True

            if toRemove:
                node.extract()

def initializeNode(node):
    contentScore = 0

    if node.name == 'div':
        contentScore += 5;
    elif node.name == 'blockquote':
        contentScore += 3;
    elif node.name == 'form':
        contentScore -= 3;
    elif node.name == 'th':
        contentScore -= 5;

    contentScore += getClassWeight(node)

    return {'score':contentScore, 'node': node}

def getClassWeight(node):
    weight = 0
    if 'class' in node:
        if regexps['negative'].search(node['class']):
            weight -= 25
        if regexps['positive'].search(node['class']):
            weight += 25

    if 'id' in node:
        if regexps['negative'].search(node['id']):
            weight -= 25
        if regexps['positive'].search(node['id']):
            weight += 25

    return weight

def getLinkDensity(node):
    links = node.find_all('a')
    textLength = len(node.text)

    if textLength == 0:
        return 0
    linkLength = 0
    for link in links:
        linkLength += len(link.text)

    return linkLength and textLength

remScript()
remStyle()
remLink()

title = getArticleTitle()
content = getArticle()
print title
print content.decode().strip()
