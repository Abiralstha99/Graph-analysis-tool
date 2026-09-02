import React, { useState } from 'react';
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalFooter,
    ModalBody,
    ModalCloseButton,
    Button,
    FormControl,
    FormLabel,
    Input,
    VStack,
    useToast,
    InputGroup,
    InputRightElement,
    IconButton,
    Text,
    Alert,
    AlertIcon,
    AlertDescription,
    Progress,
    useColorModeValue,
} from '@chakra-ui/react';
import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';
import { changePassword } from '../api/auth';

interface ChangePasswordDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

const ChangePasswordDialog: React.FC<ChangePasswordDialogProps> = ({ isOpen, onClose }) => {
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
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

    const passwordStrength = getPasswordStrength(newPassword);

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

    const handleClose = () => {
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setError('');
        setShowCurrentPassword(false);
        setShowNewPassword(false);
        setShowConfirmPassword(false);
        onClose();
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validation
        if (!currentPassword) {
            setError('Current password is required');
            return;
        }

        if (!newPassword) {
            setError('New password is required');
            return;
        }

        if (newPassword.length < 6) {
            setError('New password must be at least 6 characters');
            return;
        }

        if (newPassword !== confirmPassword) {
            setError('New passwords do not match');
            return;
        }

        if (currentPassword === newPassword) {
            setError('New password must be different from current password');
            return;
        }

        setIsLoading(true);

        try {
            await changePassword({
                current_password: currentPassword,
                new_password: newPassword,
            });

            toast({
                title: 'Password Changed',
                description: 'Your password has been successfully updated.',
                status: 'success',
                duration: 5000,
                isClosable: true,
            });

            handleClose();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to change password';
            setError(errorMessage);
            toast({
                title: 'Error',
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
        <Modal isOpen={isOpen} onClose={handleClose} size="md">
            <ModalOverlay />
            <ModalContent>
                <form onSubmit={handleSubmit}>
                    <ModalHeader>Change Password</ModalHeader>
                    <ModalCloseButton />

                    <ModalBody>
                        <VStack spacing={4}>
                            {error && (
                                <Alert status="error" borderRadius="md">
                                    <AlertIcon />
                                    <AlertDescription fontSize="sm">{error}</AlertDescription>
                                </Alert>
                            )}

                            <FormControl isRequired>
                                <FormLabel>Current Password</FormLabel>
                                <InputGroup>
                                    <Input
                                        type={showCurrentPassword ? 'text' : 'password'}
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        placeholder="Enter current password"
                                    />
                                    <InputRightElement>
                                        <IconButton
                                            aria-label={showCurrentPassword ? 'Hide password' : 'Show password'}
                                            icon={showCurrentPassword ? <ViewOffIcon /> : <ViewIcon />}
                                            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                            variant="ghost"
                                            size="sm"
                                        />
                                    </InputRightElement>
                                </InputGroup>
                            </FormControl>

                            <FormControl isRequired>
                                <FormLabel>New Password</FormLabel>
                                <InputGroup>
                                    <Input
                                        type={showNewPassword ? 'text' : 'password'}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="Enter new password"
                                    />
                                    <InputRightElement>
                                        <IconButton
                                            aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                                            icon={showNewPassword ? <ViewOffIcon /> : <ViewIcon />}
                                            onClick={() => setShowNewPassword(!showNewPassword)}
                                            variant="ghost"
                                            size="sm"
                                        />
                                    </InputRightElement>
                                </InputGroup>
                                {newPassword && (
                                    <VStack align="stretch" mt={2} spacing={1}>
                                        <Progress
                                            value={passwordStrength}
                                            size="sm"
                                            colorScheme={getStrengthColor(passwordStrength)}
                                            borderRadius="full"
                                        />
                                        <Text fontSize="xs" color={useColorModeValue(`${getStrengthColor(passwordStrength)}.600`, `${getStrengthColor(passwordStrength)}.400`)}>
                                            Password strength: {getStrengthText(passwordStrength)}
                                        </Text>
                                    </VStack>
                                )}
                                <Text fontSize="xs" color={useColorModeValue('gray.500', 'gray.400')} mt={1}>
                                    Must be at least 6 characters
                                </Text>
                            </FormControl>

                            <FormControl isRequired>
                                <FormLabel>Confirm New Password</FormLabel>
                                <InputGroup>
                                    <Input
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="Confirm new password"
                                    />
                                    <InputRightElement>
                                        <IconButton
                                            aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                                            icon={showConfirmPassword ? <ViewOffIcon /> : <ViewIcon />}
                                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                            variant="ghost"
                                            size="sm"
                                        />
                                    </InputRightElement>
                                </InputGroup>
                                {confirmPassword && newPassword !== confirmPassword && (
                                    <Text fontSize="xs" color={useColorModeValue('red.500', 'red.400')} mt={1}>
                                        Passwords do not match
                                    </Text>
                                )}
                            </FormControl>
                        </VStack>
                    </ModalBody>

                    <ModalFooter>
                        <Button variant="ghost" mr={3} onClick={handleClose}>
                            Cancel
                        </Button>
                        <Button
                            colorScheme="blue"
                            type="submit"
                            isLoading={isLoading}
                            isDisabled={
                                !currentPassword ||
                                !newPassword ||
                                !confirmPassword ||
                                newPassword !== confirmPassword ||
                                newPassword.length < 6
                            }
                        >
                            Change Password
                        </Button>
                    </ModalFooter>
                </form>
            </ModalContent>
        </Modal>
    );
};

export default ChangePasswordDialog;
