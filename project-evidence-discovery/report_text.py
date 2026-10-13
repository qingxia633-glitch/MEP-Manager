"""Narrow vl-prin1-to-string decoder. Preserve the original literal separately."""
import re

def serialized_field(text,key):
    match=re.search(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)
    return match[1].strip() if match else None

def decode_exported_string(literal):
    if not isinstance(literal,str) or len(literal)<2 or literal[0]!='"' or literal[-1]!='"':
        raise ValueError('Expected quoted exporter string')
    result=[];i=1
    escapes={'\\':'\\','"':'"','n':'\n','r':'\r','t':'\t'}
    while i<len(literal)-1:
        char=literal[i]
        if char=='\\':
            i+=1
            if i>=len(literal)-1 or literal[i] not in escapes:
                raise ValueError('Unverified exporter escape')
            result.append(escapes[literal[i]])
        elif char=='"':raise ValueError('Unescaped quote in exporter string')
        else:result.append(char)
        i+=1
    return ''.join(result)

def text_record(literal):
    try:
        return {'raw_serialized_text':literal,'decoded_text':decode_exported_string(literal),'text_decode_status':'read'}
    except ValueError:
        return {'raw_serialized_text':literal,'decoded_text':None,'text_decode_status':'unresolved'}
