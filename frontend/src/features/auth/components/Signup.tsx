import React, { useState } from 'react';
import {
    Box,
    Button,
    Container,
    FormControl,
    FormLabel,
    Heading,
    Input,
    Stack,
    Text,
    useToast,
    VStack,
    Link as ChakraLink,
    InputGroup,
    InputRightElement,
    IconButton,
    Alert,
    AlertIcon,
    AlertDescription,
    FormHelperText,
    Progress,
    useColorModeValue,
} from '@chakra-ui/react';
import { ViewIcon, ViewOffIcon, CheckIcon } from '@chakra-ui/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ColorModeToggle from '../../../components/shared/ColorModeToggle';

const Signup: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const { register } = useAuth();
    const navigate = useNavigate();
    const toast = useToast();

    // Password strength indicator
    const getPasswordStrength = (pass: string): number => {
        let strength = 0;
        if (pass.length >= 8) strength += 25;
        if (pass.length >= 12) strength += 25;
        if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) strength += 25;
        if (/[0-9]/.test(pass)) strength += 15;
        if (/[^a-zA-Z0-9]/.test(pass)) strength += 10;
        return Math.min(strength, 100);
    };

    const passwordStrength = getPasswordStrength(password);

    const getStrengthColor = (strength: number): string => {
        if (strength < 40) return 'red';
        if (strength < 70) return 'yellow';
        return 'green';
    };

    const getStrengthText = (strength: number): string => {
        if (strength < 40) return 'Weak';
        if (strength < 70) return 'Moderate';
        return 'Strong';
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validation
        if (!username.trim()) {
            setError('Username is required');
            return;
        }

        if (username.length < 3) {
            setError('Username must be at least 3 characters');
            return;
        }

        if (!password) {
            setError('Password is required');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setIsLoading(true);

        try {
            await register(username, password);
            toast({
                title: 'Account Created',
                description: `Welcome to MRG Labs, ${username}!`,
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
            navigate('/dashboard');
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Registration failed';
            setError(errorMessage);
            toast({
                title: 'Registration Failed',
                description: errorMessage,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Box minH="100vh" bg={useColorModeValue('gray.50', 'gray.900')} display="flex" alignItems="center" justifyContent="center" position="relative">
            {/* Color Mode Toggle - Top Right */}
            <Box position="absolute" top={4} right={4}>
                <ColorModeToggle />
            </Box>

            <Container maxW="md" py={12}>
                <VStack spacing={8} bg={useColorModeValue('white', 'gray.800')} p={8} borderRadius="lg" boxShadow="xl">
                    {/* Logo/Header */}
                    <VStack spacing={2}>
                        <Heading size="xl" color={useColorModeValue('blue.600', 'blue.400')}>
                            MRG Labs
                        </Heading>
                        <Text color={useColorModeValue('gray.600', 'gray.400')} fontSize="lg">
                            Graphing Application
                        </Text>
                    </VStack>

                    {/* Signup Form */}
                    <Box w="100%">
                        <form onSubmit={handleSubmit}>
                            <Stack spacing={4}>
                                <Heading size="md" textAlign="center">
                                    Create Account
                                </Heading>

                                {error && (
                                    <Alert status="error" borderRadius="md">
                                        <AlertIcon />
                                        <AlertDescription fontSize="sm">{error}</AlertDescription>
                                    </Alert>
                                )}

                                <FormControl isRequired>
                                    <FormLabel>Username</FormLabel>
                                    <Input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="Choose a username"
                                        size="lg"
                                        autoFocus
                                    />
                                    <FormHelperText>At least 3 characters</FormHelperText>
                                </FormControl>

                                <FormControl isRequired>
                                    <FormLabel>Password</FormLabel>
                                    <InputGroup size="lg">
                                        <Input
                                            type={showPassword ? 'text' : 'password'}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder="Create a password"
                                        />
                                        <InputRightElement>
                                            <IconButton
                                                aria-label={showPassword ? 'Hide password' : 'Show password'}
                                                icon={showPassword ? <ViewOffIcon /> : <ViewIcon />}
                                                onClick={() => setShowPassword(!showPassword)}
                                                variant="ghost"
                                                size="sm"
                                            />
                                        </InputRightElement>
                                    </InputGroup>
                                    {password && (
                                        <VStack align="stretch" mt={2} spacing={1}>
                                            <Progress
                                                value={passwordStrength}
                                                size="sm"
                                                colorScheme={getStrengthColor(passwordStrength)}
                                                borderRadius="full"
                                            />
                                            <Text fontSize="xs" color={`${getStrengthColor(passwordStrength)}.600`}>
                                                Password strength: {getStrengthText(passwordStrength)}
                                            </Text>
                                        </VStack>
                                    )}
                                    <FormHelperText>At least 6 characters</FormHelperText>
                                </FormControl>

                                <FormControl isRequired>
                                    <FormLabel>Confirm Password</FormLabel>
                                    <InputGroup size="lg">
                                        <Input
                                            type={showConfirmPassword ? 'text' : 'password'}
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="Confirm your password"
                                        />
                                        <InputRightElement>
                                            {confirmPassword && password === confirmPassword ? (
                                                <CheckIcon color="green.500" />
                                            ) : (
                                                <IconButton
                                                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                                                    icon={showConfirmPassword ? <ViewOffIcon /> : <ViewIcon />}
                                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                    variant="ghost"
                                                    size="sm"
                                                />
                                            )}
                                        </InputRightElement>
                                    </InputGroup>
                                    {confirmPassword && password !== confirmPassword && (
                                        <Text fontSize="xs" color="red.500" mt={1}>
                                            Passwords do not match
                                        </Text>
                                    )}
                                </FormControl>

                                <Button
                                    type="submit"
                                    colorScheme="blue"
                                    size="lg"
                                    fontSize="md"
                                    isLoading={isLoading}
                                    loadingText="Creating account..."
                                    w="100%"
                                    isDisabled={!username || !password || !confirmPassword || password !== confirmPassword}
                                >
                                    Sign Up
                                </Button>
                            </Stack>
                        </form>
                    </Box>

                    {/* Login Link */}
                    <Text color={useColorModeValue('gray.600', 'gray.400')} fontSize="sm">
                        Already have an account?{' '}
                        <ChakraLink as={Link} to="/login" color={useColorModeValue('blue.600', 'blue.400')} fontWeight="semibold">
                            Sign In
                        </ChakraLink>
                    </Text>
                </VStack>
            </Container>
        </Box>
    );
};

export default Signup;
