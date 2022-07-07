# Poly
**!!! Work In Progress !!!**
## How it works
When the engine receives a piece of source code, it:
1. creates the AST (abstract syntax tree) of the code, then
2. shuffles the tree by repeatedly swapping two random nodes, then
3. alters leaf nodes (e.g. changing `break` to `continue`, changing `+` to `-`)
4. fixes the AST to make it compliant with syntax (e.g. add `pass` to empty `if` or `for` body), then
5. reassembles the AST to real code.

The real code we get is the *payload*. We also get the *key*: a series of steps that describes how we swapped the AST 
during obfuscation.

An unpacker is just a script that undo the steps.

This is a simple polymorphic engine. It still exposes the unpacker. Thus, I propose an improvement.

### Shuffle Wisely

(Inspired by [Q](https://www.usenix.org/legacy/events/sec11/tech/full_papers/Schwartz.pdf) and 
[Frankenstein](https://personal.utdallas.edu/~hamlen/mohan12woot.pdf)) 
Since the *payload* itself is executable, why don't we tailor the unpacker by making it invoke some routines in the 
*payload* to fulfill the same unpaking requirements?

To achieve this, instead of randomly swapping nodes, we need to shuffle the AST wisely. For example, we can deliberately
alter the syntax tree to form a function which contains a block that recursively read a tree. This function can be a 
helper function of the unpacker.

### Future works

Furthermore, the obfuscation can be even more complex if helper functions in the *payload* need to be 'un-shuffle' by 
the unpacker first.

unpacker un-shuffles the helper function -> unpacker uses the helper function to un-shuffle another helper function 
-> ... -> unpacker is now able to un-shuffle the payload to the original code.