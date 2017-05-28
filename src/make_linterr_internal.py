import json
import re
from StringIO import StringIO

CONF = 'linterr_code.json'
ML = 'linterr_internal.ml'
MLI = 'linterr_internal.mli'

MODNAME = 'LintErrorCode'
HEADER = """(* This file is generated by make_linterrorcode.py. Do not edit! *)

"""

INTF_HEADER = HEADER + """open Ast

module LogLv : sig

  type t =
    | Fatal
    | Error
    | Warn

  val to_int : t -> int
  val tag : t -> string

end

module Code : sig

"""

INTF_FOOTER = """  val category : t -> string
  val num : t -> int
  val loglv : t -> LogLv.t
  val tag : t -> string
  val message : t -> string

end
"""

DEF_HEADER = HEADER + """open Core.Std
open Ast

module LogLv = struct

  type t =
    | Fatal
    | Error
    | Warn

  let to_int = function
  | Fatal -> 0
  | Error -> 1
  | Warn -> 2

  let tag = function
  | Fatal -> "F"
  | Error -> "E"
  | Warn -> "W"

end

module Code = struct

"""

DEF_FOOTER = """  let tag code =
    let t = LogLv.tag (loglv code)
    in
    sprintf "%s%d" t (num code)

end
"""

class Code(object):

    def __init__(self, data):
        self.category = data['category']
        self.num = data['num']
        self.loglv = data.get('loglv', 'Error')
        self.type_ = data['type']
        self.param_types = data.get('param_types')
        self.message = data['message']
        self.doc = data.get('doc')
        self.param_doc = data.get('param_doc')

def run():
    s = open(CONF).read()
    conf = json.loads(s)
    codes = [Code(data) for data in conf]
    make_mli(codes)
    make_ml(codes)

def make_mli(conf):
    f = StringIO()
    f.write(INTF_HEADER)
    write_type(f, conf, True)
    f.write(INTF_FOOTER)
    open(MLI, 'w').write(f.getvalue().encode('utf8'))

def make_ml(conf):
    f = StringIO()
    f.write(DEF_HEADER)
    write_type(f, conf, False)
    write_category(f, conf)
    write_num(f, conf)
    write_loglv(f, conf)
    write_message(f, conf)
    f.write(DEF_FOOTER)
    open(ML, 'w').write(f.getvalue().encode('utf8'))

def write_type(f, conf, mli):
    f.write("  type t =\n")
    for code in conf:
        f.write("    | " + code.type_)
        if code.param_types:
            f.write(" of ")
            f.write(" * ".join(code.param_types))
        f.write("\n")
        if mli and code.doc:
            f.write("    (** " + code.doc)
            if code.param_types:
                f.write("\n     *\n")
                for i in range(len(code.param_types)):
                    f.write("     * " + code.param_types[i])
                    if code.param_doc:
                        f.write(": " + code.param_doc[i])
                    f.write("\n")
                f.write("     *)\n")
            else:
                f.write(" *)\n")
        f.write("\n")
    f.write("\n")

def write_category(f, conf):
    f.write("  let category code =\n")
    def func(f, code, indent):
        f.write('"' + code.category + '"')
    write_match(f, conf, func)

def write_num(f, conf):
    f.write("  let num code =\n")
    def func(f, code, indent):
        f.write(code.num)
    write_match(f, conf, func)

def write_loglv(f, conf):
    f.write("  let loglv code =\n")
    def func(f, code, indent):
        f.write("LogLv." + code.loglv)
    write_match(f, conf, func)

def write_message(f, conf):
    f.write("  let message code =\n")
    def func(f, code, indent):
        f.write("sprintf " + to_format(code.message) + " ")
        f.write(to_format_args(code.message, code.param_types))
    write_match(f, conf, func)

def to_format(msg):
    msg = re.sub("\$\d+", "%s", msg)
    msg = re.sub('"', '\"', msg)
    return '"' + msg + '"'

def to_format_args(msg, ptypes):
    args = []
    for m in re.finditer("\$(\d+)", msg):
        i = int(m.group(1)) - 1
        t = ptypes[i]
        var = "_p" + str(i)
        if t == 'string':
            code = var
        elif t == 'int':
            code = "(Int.to_string " + var + ")"
        elif t.endswith('.t'):
            code = "(" + t[:-1] + "to_string " + var + ")"
        else:
            raise StandardError(u"Unsupported parameter type: " + t)
        args.append(code)
    return ' '.join(args)

def write_match(f, conf, func):
    f.write("    match code with\n")
    for code in conf:
        f.write("    | " + code.type_)
        if code.param_types:
            f.write(" (")
            f.write(', '.join(["_p" + str(i) for i in range(len(code.param_types))]))
            f.write(")")
        f.write(" -> ")
        func(f, code, "    ")
        f.write("\n")
    f.write("\n")

if __name__ == "__main__":
    run()