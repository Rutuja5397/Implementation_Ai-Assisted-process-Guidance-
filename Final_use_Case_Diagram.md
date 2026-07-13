@startuml
left to right direction
skinparam shadowing false
skinparam packageStyle rectangle
skinparam usecase {
    BackgroundColor #EEF2FF
    BorderColor     #5555AA
    FontSize        11
}
skinparam actor {
    BackgroundColor #DDEEFF
    BorderColor     #2255AA
    FontSize        11
}
skinparam rectangle {
    BackgroundColor #F8F8FF
    BorderColor     #7777BB
    FontSize        12
}
skinparam database {
    BackgroundColor #FFF8EE
    BorderColor     #AA7733
    FontSize        11
}
skinparam cloud {
    BackgroundColor #EEFFEE
    BorderColor     #338833
    FontSize        11
}
skinparam note {
    BackgroundColor #F8F8FF
    BorderColor     #7777BB
    FontSize        12
}
skinparam ArrowColor    #444444
skinparam ArrowFontSize 10

actor "Maintenance\nEngineer" as ME

rectangle "Process Guidance " {
    (Log Fault &\nStart Session)           as UC1
    (Request AI\nDiagnostic Guidance)      as UC2
    (Record Field\nMeasurements)           as UC4
    (Request Fault\nDiagnosis Report)      as UC5
    (Escalate Fault\nto SME)               as UC6
    (Capture Fault\nContext & State)       as UC1r
    (Deliver Step-by-Step\nGuidance)       as UC2r
    (Analyse Measurement\nReadings)        as UC4r
    (Generate Traceable\nFault Report)     as UC5r
    (Notify & Assign\nSME Review)          as UC6r
}



cloud "LLM\nEngine" as LLM {
    (Generate Diagnostic\nAI Response) as UC_LLM
}
database "Crane\nKnowledge Base" as KB {
    (Retrieve Maintenance\nProcedures) as UC_KB
}
actor "Senior Engineer\n(SME)" as SME

ME --> UC1 : INITIATE
ME --> UC2 : REQUEST
ME --> UC4 : RECORD
ME --> UC5 : REQUEST
ME --> UC6 : ESCALATE

UC1 ..> UC1r
UC2 ..> UC2r
UC4 ..> UC4r
UC5 ..> UC5r
UC6 ..> UC6r

UC2r -left-> ME : RECEIVE

UC2    -down->  UC_KB  : QUERY
UC_KB  -right-> UC_LLM : provides context
UC_LLM -left->  UC2r   : GENERATE
UC4r   -down->  UC5r   : informs
UC6r   -down->  SME    : NOTIFY

UC_LLM -[hidden]up-> UC_KB

@enduml

