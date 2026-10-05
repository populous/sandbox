grammar Arithmetic;

expression
    : additive
    ;

additive
    : multiplicative ((PLUS | MINUS) multiplicative)*
    ;

multiplicative
    : unary ((STAR | SLASH) unary)*
    ;

unary
    : (PLUS | MINUS) unary
    | primary
    ;

primary
    : NUMBER
    | IDENTIFIER
    | LPAREN expression RPAREN
    ;

PLUS: '+';
MINUS: '-';
STAR: '*';
SLASH: '/';
LPAREN: '(';
RPAREN: ')';
NUMBER: [0-9]+;
IDENTIFIER: [a-zA-Z_][a-zA-Z_0-9]*;
WS: [ \t\r\n]+ -> skip;
