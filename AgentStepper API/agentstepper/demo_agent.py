import os
import json
from typing import Union, Dict
from uuid import uuid4
from Client.debugger_client import AgentDebugger
import argparse
import time

class DummyAgent:
    def __init__(self, workspace_path: str, host:str, port):
        self.workspace_path = workspace_path
        self.host = host
        self.port = port
        self.tools = {
            "create_folder": self.create_folder,
            "write_file": self.write_file,
            "run_tests": self.run_tests
        }
        # Predefined sequence of LLM prompts and responses for the demo
        self.cycles = [
            # Cycle 1: Create project structure
            {
                "prompt": {
                    "task": "Start developing a Hangman game in Java. Decide the next action.",
                    "context": "Initial setup for a Maven-based Java project."
                },
                "response": {
                    "decision": "Create the project directory structure.",
                    "tool_call": {
                        "tool": "create_folder",
                        "args": {"path": "src/main/java/hangman"}
                    }
                },
                "tool_result": {"status": "success", "message": "Folder src/main/java/hangman created."}
            },
            # Cycle 2: Create Maven POM file
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Project structure created. Need build configuration."
                },
                "response": {
                    "decision": "Create a Maven POM file.",
                    "tool_call": {
                        "tool": "write_file",
                        "args": {
                            "path": "pom.xml",
                            "content": """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>hangman</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.8.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""
                        }
                    }
                },
                "tool_result": {"status": "success", "message": "File pom.xml written successfully."}
            },
            # Cycle 3: Create WordList class
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Maven POM file created. Need to implement word selection logic."
                },
                "response": {
                    "decision": "Create a WordList class to manage game words.",
                    "tool_call": {
                        "tool": "write_file",
                        "args": {
                            "path": "src/main/java/hangman/WordList.java",
                            "content": """package hangman;

import java.util.Arrays;
import java.util.List;
import java.util.Random;

public class WordList {
    private List<String> words = Arrays.asList("JAVA", "PYTHON", "KOTLIN");
    private Random random = new Random();

    public String getRandomWord() {
        return words.get(random.nextInt(words.size()));
    }
}
"""
                        }
                    }
                },
                "tool_result": {"status": "success", "message": "File src/main/java/hangman/WordList.java written successfully."}
            },
            # Cycle 4: Create HangmanGame class (with intentional bug)
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "WordList class created. Need main game logic."
                },
                "response": {
                    "decision": "Create the HangmanGame class with core game logic.",
                    "tool_call": {
                        "tool": "write_file",
                        "args": {
                            "path": "src/main/java/hangman/HangmanGame.java",
                            "content": """package hangman;

import java.util.Scanner;

public class HangmanGame {
    private String word;
    private char[] guessedWord;
    private int attemptsLeft = 6;

    public HangmanGame() {
        WordList wordList = new WordList();
        this.word = wordList.getRandomWord();
        this.guessedWord = new char[word.length()];
        for (int i = 0; i < word.length(); i++) {
            guessedWord[i] = '_'; // Bug 1: Doesn't initialize spaces correctly
        }
    }

    public void play() {
        Scanner scanner = new Scanner(System.in);
        while (attemptsLeft > 0 && !isWordGuessed()) {
            System.out.println("Word: " + String.valueOf(guessedWord));
            System.out.println("Attempts left: " + attemptsLeft);
            System.out.print("Guess a letter: ");
            char guess = scanner.next().toUpperCase().charAt(0);
            boolean correct = false;
            for (int i = 0; i < word.length(); i++) {
                if (word.charAt(i) == guess) {
                    guessedWord[i] = guess;
                    correct = true;
                }
            }
            if (!correct) {
                attemptsLeft--; // Bug 2: Decrements attempts even for repeated guesses
            }
        }
        if (isWordGuessed()) {
            System.out.println("You won! The word was: " + word);
        } else {
            System.out.println("Game over! The word was: " + word);
        }
    }

    private boolean isWordGuessed() {
        return String.valueOf(guessedWord).equals(word);
    }

    public static void main(String[] args) {
        HangmanGame game = new HangmanGame();
        game.play();
    }
}
"""
                        }
                    }
                },
                "tool_result": {"status": "success", "message": "File src/main/java/hangman/HangmanGame.java written successfully."}
            },
            # Cycle 5: Create test folder
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "HangmanGame class created. Need to set up testing."
                },
                "response": {
                    "decision": "Create the test directory structure.",
                    "tool_call": {
                        "tool": "create_folder",
                        "args": {"path": "src/test/java/hangman"}
                    }
                },
                "tool_result": {"status": "success", "message": "Folder src/test/java/hangman created."}
            },
            # Cycle 6: Create unit tests
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Test directory created. Need to write unit tests."
                },
                "response": {
                    "decision": "Write unit tests for HangmanGame.",
                    "tool_call": {
                        "tool": "write_file",
                        "args": {
                            "path": "src/test/java/hangman/HangmanGameTest.java",
                            "content": """package hangman;

import org.junit.Test;
import static org.junit.Assert.*;

public class HangmanGameTest {
    @Test
    public void testInitialGuessedWord() {
        HangmanGame game = new HangmanGame();
        String word = game.getWord(); // Assume getter added for testing
        char[] guessed = game.getGuessedWord(); // Assume getter added
        assertEquals(word.length(), guessed.length);
        for (char c : guessed) {
            assertEquals('_', c);
        }
    }

    @Test
    public void testRepeatedGuess() {
        HangmanGame game = new HangmanGame();
        int initialAttempts = game.getAttemptsLeft(); // Assume getter added
        game.makeGuess('X'); // Assume method added for testing
        int afterFirst = game.getAttemptsLeft();
        game.makeGuess('X');
        assertEquals(afterFirst, game.getAttemptsLeft());
    }
}
"""
                        }
                    }
                },
                "tool_result": {"status": "success", "message": "File src/test/java/hangman/HangmanGameTest.java written successfully."}
            },
            # Cycle 7: Run tests
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Unit tests written. Need to validate code."
                },
                "response": {
                    "decision": "Run unit tests to identify issues.",
                    "tool_call": {
                        "tool": "run_tests",
                        "args": {}
                    }
                },
                "tool_result": {
                    "status": "failure",
                    "message": "Tests failed: testInitialGuessedWord (expected '_' but got uninitialized chars), testRepeatedGuess (attempts decremented on repeated guess)."
                }
            },
            # Cycle 8: Fix bugs
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Tests failed due to uninitialized guessedWord and attempts decremented on repeated guesses. Need to fix bugs."
                },
                "response": {
                    "decision": "Update HangmanGame to fix initialization and repeated guess issues, and add test methods.",
                    "tool_call": {
                        "tool": "write_file",
                        "args": {
                            "path": "src/main/java/hangman/HangmanGame.java",
                            "content": """package hangman;

import java.util.HashSet;
import java.util.Scanner;
import java.util.Set;

public class HangmanGame {
    private String word;
    private char[] guessedWord;
    private int attemptsLeft = 6;
    private Set<Character> guessedLetters = new HashSet<>();

    public HangmanGame() {
        WordList wordList = new WordList();
        this.word = wordList.getRandomWord();
        this.guessedWord = new char[word.length()];
        for (int i = 0; i < word.length(); i++) {
            guessedWord[i] = '_';
        }
    }

    public void play() {
        Scanner scanner = new Scanner(System.in);
        while (attemptsLeft > 0 && !isWordGuessed()) {
            System.out.println("Word: " + String.valueOf(guessedWord));
            System.out.println("Attempts left: " + attemptsLeft);
            System.out.print("Guess a letter: ");
            char guess = scanner.next().toUpperCase().charAt(0);
            makeGuess(guess);
        }
        if (isWordGuessed()) {
            System.out.println("You won! The word was: " + word);
        } else {
            System.out.println("Game over! The word was: " + word);
        }
    }

    public void makeGuess(char guess) {
        if (guessedLetters.contains(guess)) {
            return;
        }
        guessedLetters.add(guess);
        boolean correct = false;
        for (int i = 0; i < word.length(); i++) {
            if (word.charAt(i) == guess) {
                guessedWord[i] = guess;
                correct = true;
            }
        }
        if (!correct) {
            attemptsLeft--;
        }
    }

    private boolean isWordGuessed() {
        return String.valueOf(guessedWord).equals(word);
    }

    // Getters for testing
    public String getWord() {
        return word;
    }

    public char[] getGuessedWord() {
        return guessedWord.clone();
    }

    public int getAttemptsLeft() {
        return attemptsLeft;
    }

    public static void main(String[] args) {
        HangmanGame game = new HangmanGame();
        game.play();
    }
}
"""
                        }
                    }
                },
                "tool_result": {"status": "success", "message": "File src/main/java/hangman/HangmanGame.java updated successfully."}
            },
            # Cycle 9: Rerun tests
            {
                "prompt": {
                    "task": "Continue developing the Hangman game. Decide the next action.",
                    "context": "Bugs fixed in HangmanGame. Need to verify fixes."
                },
                "response": {
                    "decision": "Rerun unit tests to confirm fixes.",
                    "tool_call": {
                        "tool": "run_tests",
                        "args": {}
                    }
                },
                "tool_result": {"status": "success", "message": "All tests passed."}
            }
        ]

    def create_folder(self, path: str) -> Dict:
        full_path = os.path.join(self.workspace_path, path)
        os.makedirs(full_path, exist_ok=True)
        return {"status": "success", "message": f"Folder {path} created."}

    def write_file(self, path: str, content: str) -> Dict:
        full_path = os.path.join(self.workspace_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return {"status": "success", "message": f"File {path} written successfully."}

    def run_tests(self) -> Dict:
        # Simulated test execution based on cycle context
        # In a real scenario, this would run `mvn test`
        cycle_index = self.current_cycle
        return self.cycles[cycle_index]["tool_result"]

    def run(self):
        with AgentDebugger(
            program_name='Hangman Agent',
            address=self.host,
            port=self.port,
            agent_workspace_path=self.workspace_path
        ) as debugger:
            for i, cycle in enumerate(self.cycles):
                self.current_cycle = i
                debugger.post_debug_message(f'Starting cycle {i}...')
                # Begin LLM query
                prompt = cycle["prompt"]
                updated_prompt = debugger.begin_llm_query_breakpoint(prompt)
                # Simulate LLM response (using predefined response)
                response = cycle["response"]
                time.sleep(3)
                updated_response = debugger.end_llm_query_breakpoint(response)
                
                if "tool_call" in updated_response:
                    tool_call = updated_response["tool_call"]
                    tool_name = tool_call["tool"]
                    tool_args = tool_call["args"]
                    
                    # Begin tool invocation
                    updated_args = debugger.begin_tool_invocation_breakpoint(tool_name, tool_args)
                    # Execute tool
                    tool_result = self.tools[tool_name](**updated_args)
                    time.sleep(2)
                    # End tool invocation
                    updated_result = debugger.end_tool_invocation_breakpoint(tool_result)
                    
                    # Commit changes to debugger
                    debugger.commit_agent_changes()

def main():
    parser = argparse.ArgumentParser(description="Run DummyAgent with specified host and port")
    parser.add_argument('--host', type=str, default='localhost', help='Host address for the agent (default: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='Port number for the agent (default: 8765)')
    args = parser.parse_args()
    
    agent = DummyAgent(workspace_path="agent_workspace", host=args.host, port=args.port)
    agent.run()

if __name__ == "__main__":
    main()