cmake_minimum_required(VERSION 3.20)

project(arithmetic_registers VERSION 0.1.0 LANGUAGES NONE)

option(ARITHMETIC_ENABLE_GENERAL "Build the general runtime target" ON)
option(ARITHMETIC_ENABLE_TEST "Register the pytest suite through CTest" ON)
option(ARITHMETIC_ENABLE_DOC "Build the documentation helper target" ON)
option(ARITHMETIC_ENABLE_PACT "Build the pact validation helper target" OFF)
option(ARITHMETIC_ENABLE_PROFILING "Build the profiling helper target" OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(ARITHMETIC_ENABLE_TEST)
  include(CTest)
else()
  set(BUILD_TESTING OFF)
endif()

set(ARITHMETIC_PYTHONPATH "${CMAKE_SOURCE_DIR}/src")

if(ARITHMETIC_ENABLE_GENERAL)
  add_custom_target(general ALL
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${ARITHMETIC_PYTHONPATH}" ${Python3_EXECUTABLE} -m arithmetic_registers "a + b * 2" --register a=10 --register b=3
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running the arithmetic register example"
    VERBATIM
  )
endif()

if(BUILD_TESTING AND ARITHMETIC_ENABLE_TEST)
  add_test(
    NAME pytest_wrap
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${ARITHMETIC_PYTHONPATH}" ${Python3_EXECUTABLE} -m pytest -q ${CMAKE_SOURCE_DIR}/tests
  )
  set_property(TEST pytest_wrap PROPERTY ENVIRONMENT "PYTHONPATH=${ARITHMETIC_PYTHONPATH}")
endif()

if(ARITHMETIC_ENABLE_DOC)
  add_custom_target(doc
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${ARITHMETIC_PYTHONPATH}" ${Python3_EXECUTABLE} -m pydoc arithmetic_registers
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Showing the arithmetic_registers module documentation"
    VERBATIM
  )
endif()

if(ARITHMETIC_ENABLE_PACT)
  add_custom_target(pact
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${ARITHMETIC_PYTHONPATH}" ${Python3_EXECUTABLE} -m pytest -q ${CMAKE_SOURCE_DIR}/tests
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running the contract-style validation target"
    VERBATIM
  )
endif()

if(ARITHMETIC_ENABLE_PROFILING)
  add_custom_target(profiling
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${ARITHMETIC_PYTHONPATH}" ${Python3_EXECUTABLE} -m cProfile -s cumulative -m arithmetic_registers "a + b * 2" --register a=10 --register b=3
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Profiling the arithmetic register execution path"
    VERBATIM
  )
endif()
